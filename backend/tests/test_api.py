from __future__ import annotations

import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


def wait_for(client: TestClient, job_id: str, timeout: float = 30.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("succeeded", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish")


def build(client: TestClient, **body: Any) -> dict[str, Any]:
    response = client.post("/api/jobs", json=body)
    assert response.status_code == 201, response.text
    return wait_for(client, response.json()["id"])


def test_health_reports_offline_engine(client: TestClient) -> None:
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["banner"] == "UNCLASSIFIED"
    assert health["llm"]["provider"] == "offline" and health["llm"]["enabled"] is False


def test_blueprint_catalog(client: TestClient) -> None:
    blueprints = client.get("/api/blueprints").json()
    drone = next(b for b in blueprints if b["id"] == "recon-drone")
    assert drone["stats"] == {"subsystems": 6, "modules": 13}
    layout = next(o for o in drone["options"] if o["key"] == "layout")
    assert {c["value"] for c in layout["choices"]} >= {"quad-x", "hex-x"}
    assert "applies_to" not in layout
    detail = client.get("/api/blueprints/recon-drone").json()
    assert detail["subsystems"][0]["modules"][0]["part"] == "nmea-gga-parser"
    assert client.get("/api/blueprints/warp-drive").status_code == 404


def test_request_validation(client: TestClient) -> None:
    assert client.post("/api/jobs", json={}).status_code == 422
    assert client.post("/api/jobs", json={"blueprint_id": "warp-drive"}).status_code == 404
    bad_option = {"blueprint_id": "recon-drone", "options": {"layout": "tri-y"}}
    response = client.post("/api/jobs", json=bad_option)
    assert response.status_code == 422 and "layout" in response.json()["detail"]
    assert client.get("/api/jobs/job_nope").status_code == 404


def test_build_and_download(client: TestClient, tmp_path: Path) -> None:
    job = build(client, blueprint_id="recon-drone", options={"layout": "hex-x"})
    assert job["status"] == "succeeded", job["error"]
    assert job["title"] == "Recon Drone (VX-RQ1)"
    assert job["progress"]["succeeded"] == job["progress"]["total"] == len(job["tasks"])
    checks = {c["id"]: c["status"] for c in job["inspection"]["checks"]}
    assert checks["prop-clearance"] == "warn"  # hex frame with 10 in props overlaps

    listing = client.get("/api/jobs").json()
    assert listing[0]["id"] == job["id"]

    readme = client.get(f"/api/jobs/{job['id']}/files/README.md")
    assert readme.headers["content-type"].startswith("text/markdown")
    assert "default-src 'none'" in readme.headers["content-security-policy"]
    assert "# Recon Drone (VX-RQ1)" in readme.text
    svg = client.get(f"/api/jobs/{job['id']}/files/diagrams/airframe-top.svg?download=1")
    assert svg.headers["content-type"] == "image/svg+xml"
    assert "attachment" in svg.headers["content-disposition"]
    assert client.get(f"/api/jobs/{job['id']}/files/../../etc/passwd").status_code == 404

    bundle = client.get(f"/api/jobs/{job['id']}/bundle")
    assert bundle.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(bundle.content)).namelist()
    assert "recon-drone/README.md" in names
    assert "recon-drone/src/recon_drone/flight_control/motor_mixer.py" in names
    assert len(names) == job["bundle"]["file_count"]
    manifest = json.loads(
        zipfile.ZipFile(io.BytesIO(bundle.content)).read("recon-drone/vectron.manifest.json")
    )
    assert manifest["blueprint"]["options"]["layout"] == "hex-x"


def test_module_bundle_is_self_contained(client: TestClient, tmp_path: Path) -> None:
    job = build(client, blueprint_id="recon-drone")
    response = client.get(f"/api/jobs/{job['id']}/modules/geofence/bundle")
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert "recon-drone-geofence/src/recon_drone/mission/geofence.py" in names
    assert "recon-drone-geofence/src/recon_drone/core/bus.py" in names
    assert not any("motor_mixer" in name for name in names)
    archive.extractall(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path / "recon-drone-geofence",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert client.get(f"/api/jobs/{job['id']}/modules/nope/bundle").status_code == 404


def test_event_stream_replays_and_closes(client: TestClient) -> None:
    job = build(client, blueprint_id="perimeter-radar-node")
    with client.stream("GET", f"/api/jobs/{job['id']}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        payloads = [
            json.loads(line[len("data: ") :])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]
    assert payloads[0]["type"] == "job.queued"
    assert payloads[-1]["type"] == "job.succeeded"
    assert [p["seq"] for p in payloads] == list(range(len(payloads)))

    with client.stream("GET", f"/api/jobs/{job['id']}/events?after={len(payloads) - 3}") as tail:
        rest = [line for line in tail.iter_lines() if line.startswith("data: ")]
    assert len(rest) == 2
