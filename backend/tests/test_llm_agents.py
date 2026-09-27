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
