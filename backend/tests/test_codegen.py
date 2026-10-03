"""Generated projects must be valid, lint-clean, deterministic, and pass their own tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from vectron.blueprints.catalog import BlueprintCatalog
from vectron.codegen.python.generator import PythonTarget, docwrap, py_literal
from vectron.diagrams import diagrams_markdown, render_diagrams
from vectron.domain.airframe import motor_layout, prop_clearance_mm
from vectron.domain.spec import SystemSpec

BLUEPRINTS = ["recon-drone", "ground-control-station", "perimeter-radar-node"]


def render_project(spec: SystemSpec, root: Path) -> dict[str, str]:
    target = PythonTarget()
    files = target.scaffold(spec)
    for _, module in spec.iter_modules():
        files += target.module_files(spec, target.render_module(spec, module.id))
    files += render_diagrams(spec)
    contents: dict[str, str] = {}
    for file in files:
        path = root / file.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(file.content))
        contents[file.path] = str(file.content)
    return contents


@pytest.mark.parametrize("blueprint_id", BLUEPRINTS)
def test_generated_project_passes_its_own_tests(
    catalog: BlueprintCatalog, tmp_path: Path, blueprint_id: str
) -> None:
    spec = catalog.get(blueprint_id).instantiate()
    render_project(spec, tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("blueprint_id", BLUEPRINTS)
def test_generated_project_is_lint_clean(
    catalog: BlueprintCatalog, tmp_path: Path, blueprint_id: str
) -> None:
    ruff = shutil.which("ruff")
    if ruff is None:
        pytest.skip("ruff not installed")
    render_project(catalog.get(blueprint_id).instantiate(), tmp_path)
    result = subprocess.run(
        [ruff, "check", "--no-cache", "."], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout


def test_drone_smoke_simulation_reaches_mission_mode(
    catalog: BlueprintCatalog, tmp_path: Path
) -> None:
    render_project(catalog.get("recon-drone").instantiate(), tmp_path)
    script = (
        "from recon_drone.app import run\n"
        "bus, _ = run(duration_s=3.0)\n"
        "print(bus.latest('mission.mode').mode, bus.latest('actuators.motors').armed)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(tmp_path / "src")},
        timeout=60,
    )
    assert result.stdout.split() == ["MISSION", "True"], result.stderr


def test_rendering_is_deterministic(catalog: BlueprintCatalog, tmp_path: Path) -> None:
    spec = catalog.get("recon-drone").instantiate({"layout": "octo-x"})
    first = render_project(spec, tmp_path / "a")
    second = render_project(spec, tmp_path / "b")
    assert first == second


@pytest.mark.parametrize("layout", ["quad-x", "quad-plus", "hex-x", "octo-x"])
def test_mixer_and_drawing_share_motor_geometry(catalog: BlueprintCatalog, layout: str) -> None:
    spec = catalog.get("recon-drone").instantiate({"layout": layout})
    motors = motor_layout(layout)
    source = PythonTarget().render_module(spec, "motor_mixer").source
    for motor in motors:
        assert f'("{motor.label}", {motor.angle_deg!r}, "{motor.spin}")' in source
    svg = next(d for d in render_diagrams(spec) if d.path.endswith(".svg"))
    root = ET.fromstring(str(svg.content))  # well-formed XML
    texts = {"".join(el.itertext()) for el in root.iter("{http://www.w3.org/2000/svg}text")}
    assert {f"{m.label} {m.spin}" for m in motors} <= texts


def test_prop_overlap_is_detected(catalog: BlueprintCatalog) -> None:
    spec = catalog.get("recon-drone").instantiate({"layout": "hex-x"})
    assert spec.airframe is not None
    assert prop_clearance_mm(spec.airframe) < 0
    svg = next(d for d in render_diagrams(spec) if d.path.endswith(".svg"))
    assert "PROPELLER DISCS OVERLAP" in str(svg.content)


def test_diagram_index_embeds_every_mermaid_diagram(catalog: BlueprintCatalog) -> None:
    spec = catalog.get("recon-drone").instantiate()
    diagrams = render_diagrams(spec)
    index = str(diagrams_markdown(spec, diagrams).content)
    mermaid = [d for d in diagrams if d.media_type == "text/vnd.mermaid"]
    assert index.count("```mermaid") == len(mermaid) >= 5
    assert "![Airframe, top view](diagrams/airframe-top.svg)" in index
    state = next(d for d in mermaid if d.path == "diagrams/flight-modes.mmd")
    assert "MISSION --> RTL : GEOFENCE_BREACH" in str(state.content)


def test_literals_and_docstrings_are_safe() -> None:
    assert py_literal('say "hi"\n') == '"say \\"hi\\"\\n"'
    assert py_literal((1.5,)) == "(1.5,)"
    assert py_literal(b"\x00") == "b'\\x00'"
    wrapped = docwrap('a "quoted" \\ path ' + "word " * 40, 3, 0)
    assert '"' not in wrapped and "\\" not in wrapped
    assert all(len(line) <= 96 for line in wrapped.splitlines())
