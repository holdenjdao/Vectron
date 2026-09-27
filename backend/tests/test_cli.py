from __future__ import annotations

from pathlib import Path

import pytest

from vectron.cli import main


def test_build_writes_a_runnable_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("VECTRON_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VECTRON_LLM_PROVIDER", "offline")
    code = main(["build", "recon-drone", "-o", "layout=quad-plus", "--out", str(tmp_path)])
    assert code == 0
    project = tmp_path / "recon-drone"
    assert (project / "src/recon_drone/app.py").is_file()
    assert "quad-plus" in (project / "vectron.spec.json").read_text()
    output = capsys.readouterr().out
    assert "Quartermaster" in output and "recon-drone.zip" in output


def test_bad_arguments_fail_cleanly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTRON_DATA_DIR", str(tmp_path / "data"))
    assert main(["build", "recon-drone", "-o", "layout"]) == 2
    assert main(["build", "warp-drive"]) == 2
    assert main(["build", "--brief", "a sandwich", "--out", str(tmp_path)]) == 1


def test_listings(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["blueprints"]) == 0
    assert "perimeter-radar-node" in capsys.readouterr().out
    assert main(["parts"]) == 0
    assert "multirotor-mixer" in capsys.readouterr().out
