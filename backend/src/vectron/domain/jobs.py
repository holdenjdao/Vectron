"""Build jobs, their tasks, artifacts and events (the API-facing records)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def terminal(self) -> bool:
        return self in (JobStatus.SUCCEEDED, JobStatus.FAILED)


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def terminal(self) -> bool:
        return self in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.SKIPPED)


class BuildRequest(BaseModel):
    """What the user asked the factory for."""

    model_config = ConfigDict(extra="forbid")

    blueprint_id: str | None = None
    brief: str = Field(default="", max_length=4000)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _needs_target(self) -> BuildRequest:
        self.brief = self.brief.strip()
        if not self.blueprint_id and not self.brief:
            raise ValueError("provide a blueprint_id, a mission brief, or both")
        return self


class TaskRecord(BaseModel):
    """One unit of agent work in a job's task graph."""

    id: str
    role: str
    agent: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: str = ""
    error: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_ms(self) -> int | None:
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds() * 1000)
        return None


class ArtifactKind(StrEnum):
    SOURCE = "source"
    TEST = "test"
    DIAGRAM = "diagram"
    DOC = "doc"
    CONFIG = "config"


class Artifact(BaseModel):
    """A file produced by an agent, addressed by its path inside the project."""

    path: str
    kind: ArtifactKind
    media_type: str
    title: str
    description: str = ""
    size: int
    sha256: str
    module_id: str | None = None
    producer: str


class ModuleBuild(BaseModel):
    """Build record for one generated module, including where its code came from."""

    id: str
    name: str
    subsystem: str
    class_name: str
    responsibility: str
    path: str
    test_path: str
    provenance: str
    """``part:<id>`` (parts library), ``stub`` (scaffold only) or ``llm:<model>``."""
    notes: list[str] = Field(default_factory=list)


class CheckStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class InspectionCheck(BaseModel):
    id: str
    title: str
    status: CheckStatus
    detail: str = ""
    target: str | None = None


class InspectionReport(BaseModel):
    checks: list[InspectionCheck] = Field(default_factory=list)

    def _count(self, status: CheckStatus) -> int:
        return sum(1 for c in self.checks if c.status is status)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def counts(self) -> dict[str, int]:
        return {status.value: self._count(status) for status in CheckStatus}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self._count(CheckStatus.FAIL) == 0


class BundleInfo(BaseModel):
    filename: str
    size: int
    sha256: str
    file_count: int


class LLMInfo(BaseModel):
    provider: str
    model: str | None = None


class LLMUsage(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class JobRecord(BaseModel):
    """Serializable state of a build job."""

    id: str
    status: JobStatus = JobStatus.QUEUED
    request: BuildRequest
    title: str = "New build"
    blueprint_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    llm: LLMInfo
    usage: LLMUsage = Field(default_factory=LLMUsage)
    tasks: list[TaskRecord] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    modules: list[ModuleBuild] = Field(default_factory=list)
    inspection: InspectionReport | None = None
    bundle: BundleInfo | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def progress(self) -> dict[str, int]:
        counts = {status.value: 0 for status in TaskStatus}
        for task in self.tasks:
            counts[task.status.value] += 1
        return {"total": len(self.tasks), **counts}


class JobSummary(BaseModel):
    id: str
    status: JobStatus
    title: str
    blueprint_id: str | None
    created_at: datetime
    finished_at: datetime | None
    progress: dict[str, int]

    @classmethod
    def of(cls, job: JobRecord) -> JobSummary:
        return cls(
            id=job.id,
            status=job.status,
            title=job.title,
            blueprint_id=job.blueprint_id,
            created_at=job.created_at,
            finished_at=job.finished_at,
            progress=job.progress,
        )


class JobEvent(BaseModel):
    """An entry in a job's append-only event log (streamed to clients via SSE)."""

    seq: int
    ts: datetime = Field(default_factory=utcnow)
    type: str
    job_id: str
    task_id: str | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
