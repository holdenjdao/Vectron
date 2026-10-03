"""HTTP routes. The frontend contract lives in frontend/src/api/types.ts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from vectron import __version__
from vectron.domain.jobs import BuildRequest, JobRecord, JobSummary
from vectron.orchestration import Job
from vectron.service import Factory

from .schemas import BlueprintDetail, BlueprintSummary, HealthInfo, LLMStatus

router = APIRouter()

# Job routes are ``async`` on purpose: they run on the event loop that drives the
# orchestrator, so they never observe a job record mid-update from another thread.

# Generated files are data, never active content: forbid scripts even for SVG.
FILE_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:",
    "X-Content-Type-Options": "nosniff",
}
TEXT_TYPES = ("text/", "application/json", "application/toml")
SSE_KEEPALIVE_S = 15.0
MODULE_PYPROJECT = '[tool.pytest.ini_options]\npythonpath = ["src"]\ntestpaths = ["tests"]\n'


def get_factory(request: Request) -> Factory:
    return request.app.state.factory  # type: ignore[no-any-return]


FactoryDep = Annotated[Factory, Depends(get_factory)]


def _job(factory: Factory, job_id: str) -> Job:
    job = factory.get(job_id)
    if job is None:
        raise HTTPException(404, f"unknown job {job_id!r}")
    return job


@router.get("/health", response_model=HealthInfo)
def health(factory: FactoryDep) -> HealthInfo:
    llm = factory.llm
    return HealthInfo(
        version=__version__,
        banner=factory.settings.banner,
        llm=LLMStatus(
            provider=llm.name,
            model=llm.model if llm.enabled else None,
            enabled=llm.enabled,
            detail=llm.detail,
        ),
    )


@router.get("/blueprints", response_model=list[BlueprintSummary])
def list_blueprints(factory: FactoryDep) -> list[BlueprintSummary]:
    return [BlueprintSummary.of(b) for b in factory.catalog.list()]


@router.get("/blueprints/{blueprint_id}", response_model=BlueprintDetail)
def get_blueprint(blueprint_id: str, factory: FactoryDep) -> BlueprintDetail:
    try:
        return BlueprintDetail.of(factory.catalog.get(blueprint_id))
    except KeyError as exc:
        raise HTTPException(404, str(exc.args[0])) from exc


@router.post("/jobs", response_model=JobRecord, status_code=201)
async def create_job(request: BuildRequest, factory: FactoryDep) -> JobRecord:
    try:
        job = factory.submit(request)
    except KeyError as exc:
        raise HTTPException(404, str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return job.record


@router.get("/jobs", response_model=list[JobSummary])
async def list_jobs(factory: FactoryDep) -> list[JobSummary]:
    return [JobSummary.of(job.record) for job in factory.jobs()]


@router.get("/jobs/{job_id}", response_model=JobRecord)
async def get_job(job_id: str, factory: FactoryDep) -> JobRecord:
    return _job(factory, job_id).record


@router.get("/jobs/{job_id}/events")
async def job_events(
    job_id: str,
    request: Request,
    factory: FactoryDep,
    after: int = -1,
    last_event_id: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    """Server-Sent Events: replay the job's history after ``after``, then stream live."""
    job = _job(factory, job_id)
    cursor = int(last_event_id) if last_event_id and last_event_id.isdigit() else after

    async def stream() -> AsyncIterator[str]:
        nonlocal cursor
        yield "retry: 3000\n\n"
        while True:
            events = await job.events.wait(cursor, timeout=SSE_KEEPALIVE_S)
            if await request.is_disconnected():
                return
            for event in events:
                cursor = event.seq
                yield f"id: {event.seq}\ndata: {event.model_dump_json()}\n\n"
            if job.events.closed and cursor >= len(job.events) - 1:
                return
            if not events:
                yield ": keep-alive\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/files/{path:path}")
async def job_file(job_id: str, path: str, factory: FactoryDep, download: bool = False) -> Response:
    job = _job(factory, job_id)
    artifact = next((a for a in job.record.artifacts if a.path == path), None)
    if artifact is None:
        raise HTTPException(404, f"no artifact {path!r} in {job_id}")
    media_type = artifact.media_type
    if media_type.startswith(TEXT_TYPES):
        media_type += "; charset=utf-8"
    headers = dict(FILE_HEADERS)
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{PurePosixPath(path).name}"'
    return Response(job.workspace.read(path), media_type=media_type, headers=headers)


@router.get("/jobs/{job_id}/bundle")
async def job_bundle(job_id: str, factory: FactoryDep) -> FileResponse:
    job = _job(factory, job_id)
    bundle = job.record.bundle
    if bundle is None:
        raise HTTPException(409, "the bundle is not ready yet")
    return FileResponse(
        job.workspace.bundle_path(bundle.filename),
        media_type="application/zip",
        filename=bundle.filename,
    )


@router.get("/jobs/{job_id}/modules/{module_id}/bundle")
async def module_bundle(job_id: str, module_id: str, factory: FactoryDep) -> Response:
    """One module with its tests and the core runtime it depends on, as a standalone zip."""
    job = _job(factory, job_id)
    spec = job.board.spec
    build = next((b for b in job.record.modules if b.id == module_id), None)
    if spec is None or build is None:
        raise HTTPException(404, f"module {module_id!r} has not been built in {job_id}")
    subsystem, _ = spec.module(module_id)
    package = f"src/{spec.package}"
    available = {a.path for a in job.record.artifacts}
    wanted = [
        f"{package}/__init__.py",
        f"{package}/{subsystem.id}/__init__.py",
        *(p for p in available if p.startswith(f"{package}/core/")),
        build.path,
        build.test_path,
    ]
    missing = [p for p in wanted if p not in available]
    if missing:
        raise HTTPException(409, f"module bundle incomplete, still waiting for {missing[0]}")
    extra = {
        "README.md": factory.target.module_readme(spec, module_id, provenance=build.provenance),
        "pyproject.toml": MODULE_PYPROJECT,
    }
    name = f"{spec.id}-{module_id}"
    data = job.workspace.build_zip(top=name, paths=sorted(wanted), extra=extra)
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
    )
