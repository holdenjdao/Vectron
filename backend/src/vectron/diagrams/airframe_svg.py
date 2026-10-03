"""Parametric top-view drawing of a multirotor airframe, in engineering-blueprint style.

Everything is derived from the spec's AirframeSpec, and motor numbering/spin
come from the same geometry the motor mixer code is generated from.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from xml.sax.saxutils import escape

from vectron.domain.airframe import Motor, motor_layout, prop_clearance_mm, wheelbase_mm
from vectron.domain.spec import AirframeSpec, SystemSpec

Point = tuple[float, float]

WIDTH, HEIGHT = 1000, 720
CX, CY = 350, 372  # centre of the top view
VIEW_RADIUS_PX = 250
PX_TO_MM = 25.4 / 96  # CSS pixel size at 96 dpi
ROW_H = 30  # title block row height
NICE_SCALES = (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12.5, 15, 20, 25, 30, 40, 50)

BG = "#0b2a4a"
INK = "#e6f1ff"
DIM = "#9fc9ff"
FAINT = "#7fa6cc"
CCW = "#38e0a0"
CW = "#f5b841"
WARN = "#ff6b6b"
FONT = "'JetBrains Mono', 'DejaVu Sans Mono', Consolas, monospace"


def _fmt(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _choose_scale(extent_mm: float) -> tuple[float, float]:
    """Pick a standard drawing scale 1:n that fits ``extent_mm`` in the view; returns (n, px/mm)."""
    raw = extent_mm / (VIEW_RADIUS_PX * PX_TO_MM)
    n = next((s for s in NICE_SCALES if s >= raw), math.ceil(raw))
    return n, 1.0 / (n * PX_TO_MM)


def render_airframe_svg(spec: SystemSpec, drawing_number: str | None = None) -> str:
    frame = spec.airframe
    if frame is None:
        raise ValueError("spec has no airframe")
    motors = motor_layout(frame.layout)
    prop_r_mm = frame.prop_diameter_in * 25.4 / 2
    n, s = _choose_scale(frame.arm_length_mm + prop_r_mm + 40)
    motor_r = max(10.0, frame.prop_diameter_in * 25.4 * 0.09) * s
    dwg = drawing_number or f"{spec.designation}-AF-001"

    def at(fwd_mm: float, right_mm: float) -> Point:
        return CX + right_mm * s, CY - fwd_mm * s

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" font-family="{FONT}" role="img" '
        f'aria-label="{escape(spec.name)} airframe, top view">',
        "<defs>",
        '<pattern id="minor" width="12" height="12" patternUnits="userSpaceOnUse">'
        f'<path d="M12 0H0V12" fill="none" stroke="{INK}" stroke-opacity="0.05"/></pattern>',
        '<pattern id="major" width="60" height="60" patternUnits="userSpaceOnUse">'
        '<rect width="60" height="60" fill="url(#minor)"/>'
        f'<path d="M60 0H0V60" fill="none" stroke="{INK}" stroke-opacity="0.11"/></pattern>',
        *(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" '
            f'fill="{color}"/></marker>'
            for name, color in (("ccw", CCW), ("cw", CW), ("dim", DIM), ("ink", INK))
        ),
        "</defs>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="url(#major)"/>',
        f'<rect x="10" y="10" width="{WIDTH - 20}" height="{HEIGHT - 20}" fill="none" '
        f'stroke="{INK}" stroke-width="2"/>',
        f'<rect x="22" y="22" width="{WIDTH - 44}" height="{HEIGHT - 44}" fill="none" '
        f'stroke="{INK}" stroke-width="0.8" stroke-opacity="0.7"/>',
    ]
    out += _zone_markers()

    # Propeller discs (dashed) and arms first, so the body and motors draw on top.
    for motor in motors:
        mx, my = at(frame.arm_length_mm * motor.x, frame.arm_length_mm * motor.y)
        out.append(
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{prop_r_mm * s:.1f}" fill="{DIM}" '
            f'fill-opacity="0.06" stroke="{DIM}" stroke-width="1.2" stroke-dasharray="7 5"/>'
        )
    for motor in motors:
        mx, my = at(frame.arm_length_mm * motor.x, frame.arm_length_mm * motor.y)
        out.append(
            f'<line x1="{CX}" y1="{CY}" x2="{mx:.1f}" y2="{my:.1f}" stroke="{INK}" '
            f'stroke-width="{max(4.0, 16 * s):.1f}" stroke-linecap="round" stroke-opacity="0.85"/>'
        )

    # Fuselage and components.
    bx, by = at(frame.body_length_mm / 2, -frame.body_width_mm / 2)
    out.append(
        f'<rect x="{bx:.1f}" y="{by:.1f}" width="{frame.body_width_mm * s:.1f}" '
        f'height="{frame.body_length_mm * s:.1f}" rx="{10 * s:.1f}" fill="#12375f" '
        f'stroke="{INK}" stroke-width="1.6"/>'
    )
    for number, comp in enumerate(frame.components, start=1):
        px, py = at(comp.x_mm, comp.y_mm)
        if comp.shape == "circle":
            out.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{comp.w_mm / 2 * s:.1f}" fill="none" '
                f'stroke="{DIM}" stroke-width="1.2"/>'
            )
        else:
            w, h = comp.w_mm * s, comp.h_mm * s
            out.append(
                f'<rect x="{px - w / 2:.1f}" y="{py - h / 2:.1f}" width="{w:.1f}" '
                f'height="{h:.1f}" fill="none" stroke="{DIM}" stroke-width="1.2"/>'
            )
        out.append(
            f'<text x="{px:.1f}" y="{py + 3.5:.1f}" fill="{DIM}" font-size="10" '
            f'font-weight="700" text-anchor="middle">{number}</text>'
        )

    # Motors, spin arrows and labels.
    for motor in motors:
        mx, my = at(frame.arm_length_mm * motor.x, frame.arm_length_mm * motor.y)
        color, marker = (CCW, "ccw") if motor.spin == "CCW" else (CW, "cw")
        out.append(
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{motor_r:.1f}" fill="{BG}" '
            f'stroke="{INK}" stroke-width="1.8"/>'
        )
        out.append(
            f'<text x="{mx:.1f}" y="{my + 4:.1f}" fill="{INK}" font-size="12" '
            f'font-weight="700" text-anchor="middle">{motor.label}</text>'
        )
        out.append(
            _spin_arc(mx, my, prop_r_mm * s * 0.72, motor.angle_deg, motor.spin, color, marker)
        )
        lx, ly = at(
            (frame.arm_length_mm + prop_r_mm + 16 / s) * motor.x,
            (frame.arm_length_mm + prop_r_mm + 16 / s) * motor.y,
        )
        out.append(
            f'<text x="{lx:.1f}" y="{ly + 4:.1f}" fill="{color}" font-size="10.5" '
            f'text-anchor="middle">{motor.label} {motor.spin}</text>'
        )

    out += _dimensions(frame, motors, s, at, prop_r_mm)
    out += _nose_and_axes(frame, motors, s)
    out += _side_panel(spec, frame, dwg, n, len(motors))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _spin_arc(
    mx: float, my: float, r: float, angle_deg: float, spin: str, color: str, marker: str
) -> str:
    """An arc arrow on the outer side of the prop disc showing rotor direction."""
    centre = math.radians(angle_deg - 90)  # screen angle of the arm direction
    half = math.radians(50)
    start, end = (centre - half, centre + half) if spin == "CW" else (centre + half, centre - half)
    x1, y1 = mx + r * math.cos(start), my + r * math.sin(start)
    x2, y2 = mx + r * math.cos(end), my + r * math.sin(end)
    sweep = 1 if spin == "CW" else 0
    return (
        f'<path d="M{x1:.1f} {y1:.1f} A{r:.1f} {r:.1f} 0 0 {sweep} {x2:.1f} {y2:.1f}" '
        f'fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow-{marker})"/>'
    )


def _dimensions(
    frame: AirframeSpec,
    motors: list[Motor],
    s: float,
    at: Callable[[float, float], Point],
    prop_r_mm: float,
) -> list[str]:
    out: list[str] = []
    xs = [frame.arm_length_mm * m.y for m in motors]  # rightward positions of motor centres
    fs = [frame.arm_length_mm * m.x for m in motors]  # forward positions
    span_y, span_x = max(xs) - min(xs), max(fs) - min(fs)
    reach = frame.arm_length_mm + prop_r_mm

    if span_y > 1:  # lateral motor spacing, below the view
        y_dim = CY + reach * s + 46
        x1, _ = at(0, min(xs))
        x2, _ = at(0, max(xs))
        out += _dim_line(x1, y_dim, x2, y_dim, f"{_fmt(span_y)}")
        for x, f in zip(xs, fs, strict=True):
            if abs(x - min(xs)) < 0.5 or abs(x - max(xs)) < 0.5:
                px, py = at(f, x)
                out.append(_ext_line(px, py + 8, px, y_dim + 6))
    if span_x > 1:  # longitudinal motor spacing, left of the view
        x_dim = CX - reach * s - 66
        _, y1 = at(max(fs), 0)
        _, y2 = at(min(fs), 0)
        out += _dim_line(x_dim, y1, x_dim, y2, f"{_fmt(span_x)}", vertical=True)
        for x, f in zip(xs, fs, strict=True):
            if abs(f - min(fs)) < 0.5 or abs(f - max(fs)) < 0.5:
                px, py = at(f, x)
                out.append(_ext_line(px - 8, py, x_dim - 6, py))

    # Propeller diameter leader on M1 and arm length along M1's arm.
    m1 = motors[0]
    mx, my = at(frame.arm_length_mm * m1.x, frame.arm_length_mm * m1.y)
    ex, ey = mx + prop_r_mm * s * 0.7071, my - prop_r_mm * s * 0.7071
    out.append(
        f'<path d="M{ex:.1f} {ey:.1f} L{ex + 28:.1f} {ey - 28:.1f} H{ex + 92:.1f}" fill="none" '
        f'stroke="{DIM}" stroke-width="1" marker-start="url(#arrow-dim)"/>'
    )
    out.append(
        f'<text x="{ex + 32:.1f}" y="{ey - 32:.1f}" fill="{DIM}" font-size="11">'
        f"Ø{_fmt(prop_r_mm * 2)} ({_fmt(frame.prop_diameter_in)} in)</text>"
    )
    ax, ay = at(frame.arm_length_mm * 0.55 * m1.x, frame.arm_length_mm * 0.55 * m1.y)
    out.append(
        f'<text x="{ax + 10:.1f}" y="{ay + 16:.1f}" fill="{DIM}" font-size="11">'
        f"R{_fmt(frame.arm_length_mm)}</text>"
    )
    return out


def _dim_line(
    x1: float, y1: float, x2: float, y2: float, label: str, vertical: bool = False
) -> list[str]:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    line = (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{DIM}" '
        f'stroke-width="1" marker-start="url(#arrow-dim)" marker-end="url(#arrow-dim)"/>'
    )
    if vertical:
        text = (
            f'<text x="{mx - 8:.1f}" y="{my:.1f}" fill="{DIM}" font-size="11" '
            f'text-anchor="middle" transform="rotate(-90 {mx - 8:.1f} {my:.1f})">{label}</text>'
        )
    else:
        text = (
            f'<text x="{mx:.1f}" y="{my - 6:.1f}" fill="{DIM}" font-size="11" '
            f'text-anchor="middle">{label}</text>'
        )
    return [line, text]


def _ext_line(x1: float, y1: float, x2: float, y2: float) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{DIM}" '
        f'stroke-width="0.6" stroke-dasharray="2 3"/>'
    )


def _nose_and_axes(frame: AirframeSpec, motors: list[Motor], s: float) -> list[str]:
    prop_r_mm = frame.prop_diameter_in * 25.4 / 2
    front_mm = max(frame.arm_length_mm * m.x for m in motors) + prop_r_mm
    tip = CY - front_mm * s - 44
    return [
        f'<line x1="{CX}" y1="{tip + 18:.1f}" x2="{CX}" y2="{tip:.1f}" stroke="{INK}" '
        f'stroke-width="2" marker-end="url(#arrow-ink)"/>',
        f'<text x="{CX + 8}" y="{tip + 4:.1f}" fill="{INK}" font-size="10">FWD</text>',
        # Body axes legend, bottom-left.
        f'<g transform="translate(58 {HEIGHT - 62})">',
        f'<line x1="0" y1="0" x2="0" y2="-34" stroke="{INK}" stroke-width="1.4" '
        f'marker-end="url(#arrow-ink)"/>',
        f'<line x1="0" y1="0" x2="34" y2="0" stroke="{INK}" stroke-width="1.4" '
        f'marker-end="url(#arrow-ink)"/>',
        f'<circle r="3" fill="none" stroke="{INK}"/>',
        f'<text x="-4" y="-40" fill="{INK}" font-size="10">x</text>',
        f'<text x="40" y="4" fill="{INK}" font-size="10">y</text>',
        f'<text x="8" y="16" fill="{FAINT}" font-size="9">z down (into page)</text>',
        "</g>",
    ]


def _zone_markers() -> list[str]:
    """Drawing-sheet zone letters/numbers along the border, like a real engineering sheet."""
    out: list[str] = []
    cols, rows = 8, 6
    for i in range(cols):
        x = 22 + (WIDTH - 44) * (i + 0.5) / cols
        for y in (17, HEIGHT - 13):
            out.append(
                f'<text x="{x:.0f}" y="{y}" fill="{FAINT}" font-size="8" '
                f'text-anchor="middle">{cols - i}</text>'
            )
    for j in range(rows):
        y = 22 + (HEIGHT - 44) * (j + 0.5) / rows + 3
        for x in (16, WIDTH - 16):
            out.append(
                f'<text x="{x}" y="{y:.0f}" fill="{FAINT}" font-size="8" '
                f'text-anchor="middle">{"ABCDEF"[j]}</text>'
            )
    return out


def _side_panel(
    spec: SystemSpec, frame: AirframeSpec, dwg: str, scale_n: float, motor_count: int
) -> list[str]:
    x0, width = 690, 284
    clearance = prop_clearance_mm(frame)
    mixer = next((m.id for _, m in spec.iter_modules() if m.part == "multirotor-mixer"), None)
    notes = [
        "1. DIMENSIONS IN MILLIMETRES.",
        "2. MOTORS NUMBERED CLOCKWISE FROM THE",
        f"   NOSE; SAME ORDER AS {mixer}.py." if mixer else "   NOSE, AS USED BY THE MIXER.",
        "3. ROTOR SPIN ALTERNATES, M1 CCW",
        "   (VIEWED FROM ABOVE).",
        f"4. PROP TIP CLEARANCE {_fmt(clearance)} MM.",
    ]
    out = [
        f'<text x="{x0}" y="58" fill="{INK}" font-size="13" font-weight="700" '
        f'letter-spacing="2">NOTES</text>',
    ]
    for i, note in enumerate(notes):
        color = WARN if note.startswith("4.") and clearance < 0 else DIM
        out.append(
            f'<text x="{x0}" y="{82 + i * 17}" fill="{color}" font-size="10.5" '
            f'xml:space="preserve">{escape(note)}</text>'
        )
    if clearance < 0:
        out.append(
            f'<text x="{x0}" y="{82 + len(notes) * 17 + 8}" fill="{WARN}" font-size="11" '
            f'font-weight="700">WARNING: PROPELLER DISCS OVERLAP</text>'
        )

    legend_y = 232
    out += [
        f'<text x="{x0}" y="{legend_y}" fill="{INK}" font-size="13" font-weight="700" '
        f'letter-spacing="2">LEGEND</text>',
        f'<line x1="{x0}" y1="{legend_y + 20}" x2="{x0 + 28}" y2="{legend_y + 20}" '
        f'stroke="{CCW}" stroke-width="2" marker-end="url(#arrow-ccw)"/>',
        f'<text x="{x0 + 38}" y="{legend_y + 24}" fill="{DIM}" font-size="10.5">'
        f"COUNTER-CLOCKWISE ROTOR</text>",
        f'<line x1="{x0}" y1="{legend_y + 40}" x2="{x0 + 28}" y2="{legend_y + 40}" '
        f'stroke="{CW}" stroke-width="2" marker-end="url(#arrow-cw)"/>',
        f'<text x="{x0 + 38}" y="{legend_y + 44}" fill="{DIM}" font-size="10.5">'
        f"CLOCKWISE ROTOR</text>",
        f'<circle cx="{x0 + 14}" cy="{legend_y + 62}" r="9" fill="none" stroke="{DIM}" '
        f'stroke-dasharray="4 3"/>',
        f'<text x="{x0 + 38}" y="{legend_y + 66}" fill="{DIM}" font-size="10.5">'
        f"PROPELLER DISC</text>",
    ]

    parts_y = legend_y + 92
    if frame.components:
        out.append(
            f'<text x="{x0}" y="{parts_y}" fill="{INK}" font-size="13" font-weight="700" '
            f'letter-spacing="2">PARTS</text>'
        )
        for number, comp in enumerate(frame.components[:6], start=1):
            out.append(
                f'<text x="{x0}" y="{parts_y + 6 + number * 15}" fill="{DIM}" '
                f'font-size="10.5" xml:space="preserve">{number:>2}  '
                f"{escape(comp.label.upper())}</text>"
            )

    rows = [
        ("TITLE", f"{spec.name.upper()} - AIRFRAME, TOP VIEW"),
        ("DWG NO.", dwg),
        ("LAYOUT", f"{frame.layout.upper()} / {motor_count} ROTORS"),
        ("WHEELBASE", f"{_fmt(wheelbase_mm(frame))} MM"),
        ("ARM / PROP", f"{_fmt(frame.arm_length_mm)} MM / {_fmt(frame.prop_diameter_in)} IN"),
        ("MASS (AUW)", f"{_fmt(frame.mass_kg)} KG"),
        ("SCALE", f"1:{_fmt(scale_n)}"),
    ]
    row_h = ROW_H
    top = HEIGHT - 40 - 30 - len(rows) * row_h
    out.append(
        f'<rect x="{x0 - 10}" y="{top}" width="{width}" height="{len(rows) * row_h + 30}" '
        f'fill="{BG}" stroke="{INK}" stroke-width="1.4"/>'
    )
    for i, (key, value) in enumerate(rows):
        y = top + i * row_h
        if i:
            out.append(
                f'<line x1="{x0 - 10}" y1="{y}" x2="{x0 - 10 + width}" y2="{y}" '
                f'stroke="{INK}" stroke-opacity="0.5"/>'
            )
        out.append(f'<text x="{x0}" y="{y + 12}" fill="{FAINT}" font-size="8">{key}</text>')
        out.append(
            f'<text x="{x0}" y="{y + 24}" fill="{INK}" font-size="11" '
            f'font-weight="600">{escape(value)}</text>'
        )
    footer_y = top + len(rows) * row_h
    out += [
        f'<line x1="{x0 - 10}" y1="{footer_y}" x2="{x0 - 10 + width}" y2="{footer_y}" '
        f'stroke="{INK}" stroke-width="1.4"/>',
        f'<text x="{x0}" y="{footer_y + 19}" fill="{INK}" font-size="11" font-weight="700" '
        f'letter-spacing="3">VECTRON</text>',
        f'<text x="{x0 + width - 20}" y="{footer_y + 19}" fill="{FAINT}" font-size="8.5" '
        f'text-anchor="end">GENERATED - NOT FOR MANUFACTURE</text>',
    ]
    return out
