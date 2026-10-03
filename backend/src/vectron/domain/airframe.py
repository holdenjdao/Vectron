"""Multirotor geometry shared by the airframe drawing and the motor mixer.

Keeping one definition means the motor numbers printed on the drawing are
exactly the ones the generated mixer code uses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .spec import AirframeSpec

_ROTORS = {"quad-x": (4, 45.0), "quad-plus": (4, 0.0), "hex-x": (6, 30.0), "octo-x": (8, 22.5)}


@dataclass(frozen=True)
class Motor:
    label: str
    angle_deg: float
    """Angle from the nose, clockwise seen from above."""
    spin: str
    """Rotor spin seen from above: "CW" or "CCW"."""

    @property
    def x(self) -> float:
        """Forward component of the unit arm vector."""
        return math.cos(math.radians(self.angle_deg))

    @property
    def y(self) -> float:
        """Rightward component of the unit arm vector."""
        return math.sin(math.radians(self.angle_deg))


def motor_layout(layout: str) -> list[Motor]:
    """Motors numbered clockwise from the nose; spins alternate starting CCW."""
    count, first = _ROTORS[layout]
    step = 360.0 / count
    return [
        Motor(label=f"M{i + 1}", angle_deg=first + i * step, spin="CCW" if i % 2 == 0 else "CW")
        for i in range(count)
    ]


def prop_clearance_mm(airframe: AirframeSpec) -> float:
    """Gap between adjacent propeller discs (negative means the discs overlap)."""
    count, _ = _ROTORS[airframe.layout]
    motor_spacing = 2.0 * airframe.arm_length_mm * math.sin(math.pi / count)
    return motor_spacing - airframe.prop_diameter_in * 25.4


def wheelbase_mm(airframe: AirframeSpec) -> float:
    """Diagonal motor-to-motor distance, the usual size figure for multirotors."""
    return 2.0 * airframe.arm_length_mm
