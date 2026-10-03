"""The parts library: vetted, tested implementations of common module behaviours.

A part declares the message types it consumes and produces, the config it needs
and the helpers it imports. Blueprint modules opt in with ``part: <id>``; the
Engineer agent then renders the part's template instead of a stub. Parts are
matched to topics by message type, so blueprints stay free to name topics.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from vectron.domain.airframe import motor_layout
from vectron.domain.spec import ConfigParam, ModuleSpec, StateMachineSpec, SystemSpec

AUTOMATIC_TRIGGERS = frozenset({"GEOFENCE_BREACH", "BATTERY_LOW", "BATTERY_CRITICAL"})


def _param(name: str, type_: str, default: Any, unit: str = "", doc: str = "") -> ConfigParam:
    return ConfigParam(name=name, type=type_, default=default, unit=unit, doc=doc)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Part:
    id: str
    title: str
    summary: str
    subscribes: tuple[str, ...]
    publishes: tuple[str, ...]
    config: tuple[ConfigParam, ...] = ()
    stdlib: tuple[str, ...] = ()
    """Extra stdlib imports, e.g. ``"math"`` or ``"from collections import deque"``."""
    geo: tuple[str, ...] = ()
    """Names imported from the generated ``core.geo`` helpers."""
    needs_airframe: bool = False
    needs_state_machine: bool = False
    context: Callable[[SystemSpec, ModuleSpec], dict[str, Any]] | None = field(
        default=None, compare=False
    )

    @property
    def template(self) -> str:
        return f"parts/{self.id}.py.j2"

    @property
    def test_template(self) -> str:
        return f"parts/{self.id}_test.py.j2"

    def check(self, spec: SystemSpec, module: ModuleSpec) -> list[str]:
        """Return problems that prevent using this part for ``module`` (empty = OK)."""
        problems: list[str] = []
        for direction, wanted, topics in (
            ("subscribe", self.subscribes, module.subscribes),
            ("publish", self.publishes, module.publishes),
        ):
            carried = [spec.topic(t).message for t in topics]
            for message in wanted:
                count = carried.count(message)
                if count != 1:
                    problems.append(
                        f"part {self.id} must {direction} exactly one {message} topic "
                        f"(found {count})"
                    )
        if self.needs_airframe and spec.airframe is None:
            problems.append(f"part {self.id} needs an airframe in the spec")
        if self.needs_state_machine and not module.state_machine:
            problems.append(f"part {self.id} needs module.state_machine to be set")
        return problems


def merged_config(part: Part | None, module: ModuleSpec) -> list[ConfigParam]:
    """Part defaults overridden (by name) by the module's own config entries."""
    params: dict[str, ConfigParam] = {p.name: p for p in part.config} if part else {}
    for param in module.config:
        params[param.name] = param
    return list(params.values())


# -- part-specific template context -------------------------------------


def _mixer_context(spec: SystemSpec, module: ModuleSpec) -> dict[str, Any]:
    assert spec.airframe is not None
    return {"layout": spec.airframe.layout, "motors": motor_layout(spec.airframe.layout)}


def _command_path(machine: StateMachineSpec, goal: str) -> list[str] | None:
    """Shortest list of operator commands leading from the initial state to ``goal``."""
    queue: deque[tuple[str, list[str]]] = deque([(machine.initial, [])])
    seen = {machine.initial}
    while queue:
        state, path = queue.popleft()
        if state == goal:
            return path
        for transition in machine.transitions:
            if transition.source != state or transition.trigger in AUTOMATIC_TRIGGERS:
                continue
            if transition.target not in seen:
                seen.add(transition.target)
                queue.append((transition.target, [*path, transition.trigger]))
    return None


def _supervisor_context(spec: SystemSpec, module: ModuleSpec) -> dict[str, Any]:
    assert module.state_machine is not None
    machine = spec.state_machine(module.state_machine)
    context: dict[str, Any] = {"machine": machine, "safety_triggers": sorted(AUTOMATIC_TRIGGERS)}
    for key, trigger in (("breach", "GEOFENCE_BREACH"), ("critical", "BATTERY_CRITICAL")):
        context.update({f"{key}_path": None, f"{key}_source": None, f"{key}_target": None})
        for transition in machine.transitions:
            if transition.trigger != trigger:
                continue
            path = _command_path(machine, transition.source)
            if path:
                context.update(
                    {
                        f"{key}_path": path,
                        f"{key}_source": transition.source,
                        f"{key}_target": transition.target,
                    }
                )
                break
    return context


PARTS: dict[str, Part] = {
    part.id: part
    for part in (
        Part(
            id="nmea-gga-parser",
            title="NMEA GGA parser",
            summary="Validates NMEA-0183 checksums and decodes GGA sentences into fixes.",
            subscribes=("NmeaSentence",),
            publishes=("GnssFix",),
            config=(
                _param("min_satellites", "int", 6, doc="Minimum satellites for a valid fix."),
                _param("max_hdop", "float", 2.5, doc="Maximum HDOP for a valid fix."),
            ),
        ),
        Part(
            id="complementary-nav-filter",
            title="Complementary navigation filter",
            summary="Gyro/accelerometer complementary filter for attitude plus GNSS position.",
            subscribes=("ImuSample", "GnssFix"),
            publishes=("NavState",),
            config=(_param("alpha", "float", 0.98, doc="Gyro weight of the filter (0..1)."),),
            stdlib=("math",),
            geo=("local_ned_offset", "wrap_pi"),
        ),
        Part(
            id="pid-attitude-controller",
            title="PID attitude controller",
            summary="Roll/pitch angle PID and yaw-rate P loop producing normalised torques.",
            subscribes=("AttitudeSetpoint", "NavState"),
            publishes=("TorqueCommand",),
            config=(
                _param("kp_angle", "float", 4.5, doc="Proportional gain, roll and pitch."),
                _param("ki_angle", "float", 0.05, doc="Integral gain, roll and pitch."),
                _param("kd_angle", "float", 0.35, doc="Derivative gain, roll and pitch."),
                _param("kp_yaw_rate", "float", 0.8, doc="Proportional gain on yaw rate."),
                _param("integral_limit", "float", 0.3, doc="Integrator clamp."),
                _param("max_torque", "float", 1.0, doc="Output saturation (normalised)."),
            ),
            geo=("clamp", "wrap_pi"),
        ),
        Part(
            id="multirotor-mixer",
            title="Multirotor mixer",
            summary="Maps torques and thrust to per-motor commands with a disarm interlock.",
            subscribes=("TorqueCommand", "FlightMode"),
            publishes=("MotorOutputs",),
            config=(
                _param("idle_throttle", "float", 0.06, doc="Minimum output while armed."),
                _param("disarmed_mode", "str", "DISARMED", doc="Flight mode that cuts motors."),
            ),
            stdlib=("math",),
            geo=("clamp",),
            needs_airframe=True,
            context=_mixer_context,
        ),
        Part(
            id="waypoint-sequencer",
            title="Waypoint sequencer",
            summary="Tracks the active waypoint and advances inside the acceptance radius.",
            subscribes=("MissionUpload", "NavState"),
            publishes=("GuidanceTarget",),
            config=(
                _param(
                    "acceptance_radius_m", "float", 5.0, "m", "Distance that counts as reached."
                ),
            ),
            geo=("bearing_deg", "haversine_m"),
        ),
        Part(
            id="cylinder-geofence",
            title="Cylinder geofence",
            summary="Radius and ceiling containment around home with breach reporting.",
            subscribes=("NavState",),
            publishes=("GeofenceStatus",),
            config=(
                _param("radius_m", "float", 500.0, "m", "Maximum horizontal distance from home."),
                _param("ceiling_m", "float", 120.0, "m", "Maximum height above home."),
                _param("home_lat_deg", "float", 0.0, "deg", "Home latitude (0 = first fix)."),
                _param("home_lon_deg", "float", 0.0, "deg", "Home longitude (0 = first fix)."),
            ),
            geo=("haversine_m",),
        ),
        Part(
            id="flight-mode-supervisor",
            title="Flight mode supervisor",
            summary="Table-driven mode state machine fed by commands, geofence and battery.",
            subscribes=("OperatorCommand", "GeofenceStatus", "BatteryStatus"),
            publishes=("FlightMode",),
            needs_state_machine=True,
            context=_supervisor_context,
        ),
        Part(
            id="lipo-battery-monitor",
            title="LiPo battery monitor",
            summary="Sag-compensated, filtered state of charge with LOW/CRITICAL thresholds.",
            subscribes=("BatteryReading",),
            publishes=("BatteryStatus",),
            config=(
                _param("cell_count", "int", 4, doc="Cells in series (S rating)."),
                _param("low_soc_pct", "float", 30.0, "%", "State of charge that reports LOW."),
                _param(
                    "critical_soc_pct", "float", 15.0, "%", "State of charge that reports CRITICAL."
                ),
                _param("pack_resistance_ohm", "float", 0.02, "ohm", "For sag compensation."),
                _param("smoothing", "float", 0.2, doc="Low-pass factor per reading (0..1]."),
            ),
            stdlib=("bisect",),
        ),
        Part(
            id="crc-telemetry-framer",
            title="CRC telemetry framer",
            summary="Packs vehicle state into rate-limited, CRC-16 protected binary frames.",
            subscribes=("NavState", "BatteryStatus", "FlightMode"),
            publishes=("TelemetryFrame",),
            config=(_param("downlink_hz", "float", 5.0, "Hz", "Frame rate on the downlink."),),
            stdlib=("math", "struct"),
            geo=("clamp", "wrap_pi"),
        ),
        Part(
            id="geo-pointing-gimbal",
            title="Geo-pointing gimbal",
            summary="Points a pan/tilt gimbal at a geographic point of interest.",
            subscribes=("NavState", "PointOfInterest"),
            publishes=("GimbalCommand",),
            config=(
                _param("pan_limit_deg", "float", 180.0, "deg", "Pan travel either side."),
                _param("tilt_min_deg", "float", -90.0, "deg", "Lowest tilt (straight down)."),
                _param("tilt_max_deg", "float", 30.0, "deg", "Highest tilt above horizon."),
            ),
            stdlib=("math",),
            geo=("clamp", "local_ned_offset", "wrap_180"),
        ),
    )
}


def get_part(part_id: str) -> Part:
    try:
        return PARTS[part_id]
    except KeyError:
        raise KeyError(f"unknown part {part_id!r}; available: {sorted(PARTS)}") from None
