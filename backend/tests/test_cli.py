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


def test_dev_reload_ignores_generated_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: builds write .py files; the reloader must not restart mid-build."""
    import uvicorn

    import vectron

    calls: list[dict] = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))
    assert main(["serve", "--reload"]) == 0
    package_dir = Path(vectron.__file__).resolve().parent
    assert calls[0]["reload"] is True
    assert calls[0]["reload_dirs"] == [str(package_dir)]
    assert "*.yaml" in calls[0]["reload_includes"]

    assert main(["serve"]) == 0
    assert calls[1]["reload"] is False and calls[1]["reload_dirs"] is None
