from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from vectron.blueprints.catalog import BlueprintCatalog
from vectron.domain.spec import SystemSpec
from vectron.domain.values import coerce

BASE = {
    "id": "demo",
    "name": "Demo",
    "designation": "VX-D1",
    "package": "demo",
    "summary": "A demo system.",
    "messages": [{"name": "Ping", "fields": [{"name": "count", "type": "int"}]}],
    "topics": [
        {"name": "io.ping_in", "message": "Ping", "external": True},
        {"name": "io.ping_out", "message": "Ping"},
    ],
    "subsystems": [
        {
            "id": "core_sys",
            "name": "Core",
            "modules": [
                {
                    "id": "echo",
                    "name": "Echo",
                    "responsibility": "Echo pings.",
                    "subscribes": ["io.ping_in"],
                    "publishes": ["io.ping_out"],
                }
            ],
        }
    ],
}


def spec_with(**changes: object) -> dict:
    doc = copy.deepcopy(BASE)
    doc.update(changes)
    return doc


def test_minimal_spec_is_valid_and_gains_timestamps() -> None:
    spec = SystemSpec.model_validate(BASE)
    assert [f.name for f in spec.message("Ping").fields] == ["t", "count"]
    assert spec.publishers("io.ping_out") == ["echo"]
    assert spec.subscribers("io.ping_in") == ["echo"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda d: d["subsystems"][0]["modules"][0]["subscribes"].append("io.nope"),
            "unknown topic",
        ),
        (lambda d: d["topics"].append({"name": "io.x", "message": "Nope"}), "unknown message"),
        (
            lambda d: d["subsystems"][0]["modules"].append(dict(d["subsystems"][0]["modules"][0])),
            "duplicate module",
        ),
        (
            lambda d: d["subsystems"][0]["modules"][0]["publishes"].append("io.ping_in"),
            "publishes external topic",
        ),
        (lambda d: d.update(package="class"), "reserved word"),
        (lambda d: d["messages"].append({"name": "Module"}), "reserved"),
        (lambda d: d["subsystems"][0].update(id="core"), "reserved"),
    ],
)
def test_invalid_specs_are_rejected(mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    doc = copy.deepcopy(BASE)
    mutate(doc)
    with pytest.raises(ValidationError, match=message):
        SystemSpec.model_validate(doc)


def test_state_machine_must_be_deterministic() -> None:
    machine = {
        "id": "modes",
        "title": "Modes",
        "initial": "OFF",
        "states": [{"name": "OFF"}, {"name": "ON"}],
        "transitions": [
            {"source": "OFF", "trigger": "GO", "target": "ON"},
            {"source": "OFF", "trigger": "GO", "target": "OFF"},
        ],
    }
    with pytest.raises(ValidationError, match="ambiguous"):
        SystemSpec.model_validate(spec_with(state_machines=[machine]))


def test_simulation_values_are_coerced_and_checked() -> None:
    ok = spec_with(simulation=[{"topic": "io.ping_in", "fields": {"count": 3.0}}])
    assert SystemSpec.model_validate(ok).simulation[0].fields == {"count": 3}
    bad = spec_with(simulation=[{"topic": "io.ping_in", "fields": {"count": "many"}}])
    with pytest.raises(ValidationError):
        SystemSpec.model_validate(bad)


@pytest.mark.parametrize(
    ("field_type", "value", "expected"),
    [
        ("float", 3, 3.0),
        ("int", 4.0, 4),
        ("bool", "true", True),
        ("vec3", [1, 2, 3], (1.0, 2.0, 3.0)),
        ("float[]", (1, 2), (1.0, 2.0)),
        ("bytes", "ab", b"ab"),
    ],
)
def test_coerce(field_type: str, value: object, expected: object) -> None:
    assert coerce(field_type, value) == expected


@pytest.mark.parametrize(
    ("field_type", "value"),
    [("int", 1.5), ("float", True), ("float", float("nan")), ("vec3", [1, 2]), ("str", 5)],
)
def test_coerce_rejects(field_type: str, value: object) -> None:
    with pytest.raises(ValueError):
        coerce(field_type, value)


def test_catalog_loads_every_blueprint(catalog: BlueprintCatalog) -> None:
    ids = [b.id for b in catalog.list()]
    assert {"recon-drone", "ground-control-station", "perimeter-radar-node"} <= set(ids)
    assert ids[0] == "recon-drone"  # air first


def test_options_write_into_the_spec(catalog: BlueprintCatalog) -> None:
    blueprint = catalog.get("recon-drone")
    spec = blueprint.instantiate({"layout": "hex-x", "battery_cells": "6", "ceiling_m": 90})
    assert spec.airframe is not None and spec.airframe.layout == "hex-x"
    _, battery = spec.module("battery_monitor")
    assert next(p for p in battery.config if p.name == "cell_count").default == 6
    _, fence = spec.module("geofence")
    assert next(p for p in fence.config if p.name == "ceiling_m").default == 90.0


@pytest.mark.parametrize(
    "options", [{"layout": "tri-y"}, {"arm_length_mm": 5}, {"no_such_option": 1}]
)
def test_invalid_options_are_rejected(catalog: BlueprintCatalog, options: dict) -> None:
    with pytest.raises(ValueError):
        catalog.get("recon-drone").resolve_options(options)


def test_brief_matching(catalog: BlueprintCatalog) -> None:
    assert catalog.match("small drone for night surveillance")[0][0].id == "recon-drone"
    assert catalog.match("radar to protect the base perimeter")[0][0].id == "perimeter-radar-node"
    assert catalog.match("operator console for mission planning")[0][0].id == (
        "ground-control-station"
    )
    assert catalog.match("underwater submarine") == []
