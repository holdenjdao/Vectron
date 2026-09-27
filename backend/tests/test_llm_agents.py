"""LLM-backed agent paths, driven by a scripted provider (no network)."""

from __future__ import annotations

import pytest

from vectron.agents.architect import apply_patch
from vectron.blueprints.catalog import BlueprintCatalog
from vectron.config import Settings
from vectron.domain.jobs import BuildRequest, JobStatus
from vectron.llm.base import LLMError
from vectron.service import Factory

from .fakes import ScriptedLLM

GOOD_GUIDANCE = """
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..core.bus import MessageBus
from ..core.geo import clamp
from ..core.messages import AttitudeSetpoint, FlightMode, GuidanceTarget, NavState
from ..core.module import Module


@dataclass
class GuidanceControllerConfig:
    cruise_pitch: float = -0.1
    hover_thrust: float = 0.5


class GuidanceController(Module):
    name = "guidance_controller"
    subscribes = {
        "mission.target": GuidanceTarget,
        "nav.state": NavState,
        "mission.mode": FlightMode,
    }
    publishes = {"control.attitude_sp": AttitudeSetpoint}

    def __init__(self, bus: MessageBus, config: GuidanceControllerConfig | None = None) -> None:
        super().__init__(bus, config or GuidanceControllerConfig())
        self.target: GuidanceTarget | None = None

    def handlers(self) -> Mapping[str, Callable[[Any], None]]:
        return {"mission.target": self.on_target, "nav.state": self.on_state,
                "mission.mode": self.on_state}

    def on_target(self, target: GuidanceTarget) -> None:
        self.target = target

    def on_state(self, message: Any) -> None:
        pass

    def tick(self, t: float) -> None:
        if self.target is None:
            return
        pitch = clamp(self.config.cruise_pitch, -0.3, 0.3)
        self.publish("control.attitude_sp",
                     AttitudeSetpoint(t=t, pitch=pitch, thrust=self.config.hover_thrust))
"""

GOOD_TEST = """
from recon_drone.core.bus import MessageBus
from recon_drone.core.messages import AttitudeSetpoint, GuidanceTarget
from recon_drone.flight_control.guidance_controller import GuidanceController


def test_publishes_setpoint_once_targeted():
    bus = MessageBus()
    GuidanceController(bus).start()
    out: list[AttitudeSetpoint] = []
    bus.subscribe("control.attitude_sp", out.append)
    bus.publish("mission.target", GuidanceTarget(t=0.0))
"""


def llm_factory(settings: Settings, catalog: BlueprintCatalog, answers: dict) -> Factory:
    return Factory(settings, catalog=catalog, llm=ScriptedLLM(answers))


async def test_commander_uses_the_model_to_pick_blueprint_and_options(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    llm = ScriptedLLM(
        {
            "Commander": {
                "blueprint_id": "recon-drone",
                "options": [{"key": "layout", "value": "octo-x"}, {"key": "bogus", "value": "1"}],
                "rationale": "Heavy lift needs eight rotors.",
            },
            "Architect": LLMError("model busy"),
            "Engineer": LLMError("model busy"),
        }
    )
    factory = Factory(settings, catalog=catalog, llm=llm)
    job = await factory.build(BuildRequest(brief="heavy-lift recon platform"))
    assert job.record.status is JobStatus.SUCCEEDED, job.record.error
    assert job.board.options["layout"] == "octo-x"
    assert "eight rotors" in job.record.tasks[0].summary
    # Model failures downstream degrade to deterministic output instead of failing the build.
    assert all(
        m.provenance == "stub" or m.provenance.startswith("part:") for m in job.record.modules
    )
    assert llm.calls == ["Commander", "Architect", "Engineer", "Engineer", "Engineer"]
    assert job.record.usage.calls == 1  # only successful calls are billed


async def test_architect_patch_adds_a_stub_module(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    patch = {
        "rationale": "Night work needs a thermal tracker.",
        "config_overrides": [{"module_id": "geofence", "param": "radius_m", "value": "800"}],
        "new_messages": [
            {
                "name": "ThermalTrack",
                "doc": "Hot spot.",
                "fields": [
                    {"name": "bearing_deg", "type": "float", "unit": "deg", "doc": "Bearing."}
                ],
            }
        ],
        "new_topics": [{"name": "payload.thermal", "message": "ThermalTrack", "doc": "Tracks."}],
        "new_modules": [
            {
                "subsystem_id": "payload",
                "id": "thermal_tracker",
                "name": "Thermal Tracker",
                "responsibility": "Find hot spots.",
                "subscribes": ["payload.capture"],
                "publishes": ["payload.thermal"],
            }
        ],
    }
    factory = llm_factory(settings, catalog, {"Architect": patch, "Engineer": LLMError("no")})
    job = await factory.build(BuildRequest(blueprint_id="recon-drone", brief="night overwatch"))
    assert job.record.status is JobStatus.SUCCEEDED, job.record.error
    spec = job.board.spec
    assert spec is not None
    _, fence = spec.module("geofence")
    assert next(p for p in fence.config if p.name == "radius_m").default == 800.0
    assert "thermal_tracker" in {m.id for m in job.record.modules}
    assert job.board.architect_notes.startswith("Night work")


def test_invalid_patch_is_rejected_atomically(catalog: BlueprintCatalog) -> None:
    spec = catalog.get("recon-drone").instantiate()
    patch = {
        "new_modules": [
            {
                "subsystem_id": "payload",
                "id": "rogue",
                "name": "Rogue",
                "responsibility": "x",
                "subscribes": [],
                "publishes": ["sensors.imu"],
            }
        ]
    }  # external topic
    with pytest.raises(ValueError, match="external"):
        apply_patch(spec, patch)


async def test_engineer_accepts_vetted_llm_code(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    factory = llm_factory(
        settings,
        catalog,
        {
            "Engineer": {"module_source": GOOD_GUIDANCE, "test_source": GOOD_TEST, "notes": "v1"},
        },
    )
    job = await factory.build(BuildRequest(blueprint_id="recon-drone"))
    assert job.record.status is JobStatus.SUCCEEDED, job.record.error
    modules = {m.id: m for m in job.record.modules}
    assert modules["guidance_controller"].provenance == "llm:scripted-model"
    # The same answer is invalid for the other stubs (wrong class), so they fall back.
    assert modules["health_monitor"].provenance == "stub"
    assert "rejected" in modules["health_monitor"].notes[0]
    source = job.workspace.read(modules["guidance_controller"].path).decode()
    assert "cruise_pitch" in source
    checks = {c.id: c for c in job.record.inspection.checks}  # type: ignore[union-attr]
    assert checks["llm-review"].status == "warn"


async def test_engineer_rejects_code_that_breaks_factory_rules(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    evil = GOOD_GUIDANCE.replace(
        "from typing import Any", "from typing import Any\nimport subprocess"
    )
    factory = llm_factory(
        settings,
        catalog,
        {
            "Engineer": {"module_source": evil, "test_source": GOOD_TEST, "notes": ""},
        },
    )
    job = await factory.build(BuildRequest(blueprint_id="recon-drone"))
    modules = {m.id: m for m in job.record.modules}
    assert modules["guidance_controller"].provenance == "stub"
    assert "subprocess" in modules["guidance_controller"].notes[0]


TOWER_DESIGN = {
    "name": "Airfield Control Tower",
    "designation": "VX-ACT1",
    "package": "airfield_tower",
    "summary": "Surveillance, flight strips and runway safety for a small airfield.",
    "description": "Fuses radar plots into tracks and keeps controllers aware of traffic.",
    "rationale": "A tower is a C2 system, not an aircraft.",
    "messages": [
        {
            "name": "RadarPlot",
            "doc": "Raw surveillance return.",
            "fields": [
                {"name": "range_m", "type": "float", "unit": "m", "doc": "Range."},
                {"name": "bearing_deg", "type": "float", "unit": "deg", "doc": "Bearing."},
            ],
        },
        {
            "name": "TrafficTrack",
            "doc": "Correlated aircraft track.",
            "fields": [
                {"name": "track_id", "type": "int", "unit": "", "doc": "Track number."},
                {"name": "callsign", "type": "str", "unit": "", "doc": "Callsign."},
            ],
        },
    ],
    "topics": [
        {"name": "sensors.plots", "message": "RadarPlot", "doc": "Radar input.", "external": True},
        {
            "name": "surveillance.tracks",
            "message": "TrafficTrack",
            "doc": "Tracks.",
            "external": False,
        },
    ],
    "subsystems": [
        {
            "id": "surveillance",
            "name": "Surveillance",
            "description": "Radar processing.",
            "modules": [
                {
                    "id": "track_correlator",
                    "name": "Track Correlator",
                    "responsibility": "Turn plots into tracks.",
                    "subscribes": ["sensors.plots"],
                    "publishes": ["surveillance.tracks"],
                }
            ],
        },
        {
            "id": "tower_ops",
            "name": "Tower Operations",
            "description": "Controller tools.",
            "modules": [
                {
                    "id": "runway_monitor",
                    "name": "Runway Monitor",
                    "responsibility": "Warn about runway incursions.",
                    "subscribes": ["surveillance.tracks"],
                    "publishes": [],
                }
            ],
        },
    ],
    "state_machines": [
        {
            "id": "runway_state",
            "title": "Runway state",
            "initial": "CLEAR",
            "states": [{"name": "CLEAR", "doc": "Free."}, {"name": "OCCUPIED", "doc": "In use."}],
            "transitions": [
                {"source": "CLEAR", "trigger": "ENTER", "target": "OCCUPIED"},
                {"source": "OCCUPIED", "trigger": "VACATE", "target": "CLEAR"},
            ],
        }
    ],
    "sequences": [
        {
            "id": "arrival",
            "title": "Arrival",
            "participants": [
                {"id": "radar", "label": "Radar", "kind": "actor"},
                {"id": "track_correlator", "label": "Track Correlator", "kind": "module"},
            ],
            "steps": [
                {
                    "source": "radar",
                    "target": "track_correlator",
                    "message": "RadarPlot",
                    "note": "",
                }
            ],
        }
    ],
}

NO_FIT = {"blueprint_id": "none", "options": [], "rationale": "An airfield tower is not a drone."}


async def test_commander_orders_a_new_design_when_no_blueprint_fits(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    llm = ScriptedLLM(
        {"Commander": NO_FIT, "from scratch": TOWER_DESIGN, "Engineer": LLMError("busy")}
    )
    factory = Factory(settings, catalog=catalog, llm=llm)
    job = await factory.build(BuildRequest(brief="an air traffic control tower for an airfield"))
    assert job.record.status is JobStatus.SUCCEEDED, job.record.error
    assert job.board.blueprint is None and job.board.design_from_brief
    spec = job.board.spec
    assert spec is not None and spec.package == "airfield_tower"
    assert job.record.title == "Airfield Control Tower (VX-ACT1)"
    assert {m.id for m in job.record.modules} == {"track_correlator", "runway_monitor"}
    assert job.board.architect_notes.startswith("A tower is a C2 system")
    assert llm.calls[:2] == ["Commander", "from scratch"]


async def test_invalid_design_is_sent_back_for_correction(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    broken = {**TOWER_DESIGN, "topics": TOWER_DESIGN["topics"][:1]}  # tracks topic missing
    answers: list[dict] = [broken, TOWER_DESIGN]

    class Correcting(ScriptedLLM):
        async def generate_json(self, *, system: str, **kwargs):  # type: ignore[override]
            if "from scratch" in system:
                self.answers["from scratch"] = answers.pop(0)
            return await super().generate_json(system=system, **kwargs)

    llm = Correcting({"Commander": NO_FIT, "from scratch": {}, "Engineer": LLMError("busy")})
    job = await Factory(settings, catalog=catalog, llm=llm).build(
        BuildRequest(brief="an air traffic control tower")
    )
    assert job.record.status is JobStatus.SUCCEEDED, job.record.error
    assert llm.calls.count("from scratch") == 2


async def test_offline_build_does_not_force_an_unrelated_blueprint(
    settings: Settings, catalog: BlueprintCatalog
) -> None:
    job = await Factory(settings, catalog=catalog).build(
        BuildRequest(brief="an air traffic control tower")
    )
    # Offline there is no designer: keyword matching picks the nearest blueprint,
    # and generic words like "air" no longer pull in the drone.
    assert job.record.blueprint_id != "recon-drone"
