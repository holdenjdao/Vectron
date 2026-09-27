"""The live job object: serializable record, event log, workspace and shared blackboard."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from vectron.domain.blueprint import Blueprint
from vectron.domain.jobs import JobEvent, JobRecord, TaskRecord
from vectron.domain.spec import SystemSpec

from .events import EventLog
from .workspace import Workspace

SNAPSHOT_FILE = "job.json"


class JobSnapshot(BaseModel):
    """What survives a server restart: the record, its event history and the spec."""

    record: JobRecord
    events: list[JobEvent]
    options: dict[str, Any]
    spec: SystemSpec | None
    architect_notes: str = ""


@dataclass
class Blackboard:
    """Working state agents share within one job (not part of the API record)."""

    blueprint: Blueprint | None = None
    options: dict[str, Any] = field(default_factory=dict)
    spec: SystemSpec | None = None
    architect_notes: str = ""


class Job:
    def __init__(self, record: JobRecord, workspace: Workspace) -> None:
        self.record = record
        self.workspace = workspace
        self.events = EventLog()
        self.board = Blackboard()
        self.runner: asyncio.Task[None] | None = None

    @property
    def id(self) -> str:
        return self.record.id

    def save(self) -> None:
        """Persist a finished job next to its workspace."""
        snapshot = JobSnapshot(
            record=self.record,
            events=self.events.since(-1),
            options=self.board.options,
            spec=self.board.spec,
            architect_notes=self.board.architect_notes,
        )
        (self.workspace.root / SNAPSHOT_FILE).write_text(snapshot.model_dump_json(), "utf-8")

    @classmethod
    def load(cls, root: Path) -> Job:
        snapshot = JobSnapshot.model_validate_json((root / SNAPSHOT_FILE).read_text("utf-8"))
        job = cls(snapshot.record, Workspace(root))
        job.events = EventLog.restored(snapshot.events)
        job.board = Blackboard(
            options=snapshot.options,
            spec=snapshot.spec,
            architect_notes=snapshot.architect_notes,
        )
        return job

    def task(self, task_id: str) -> TaskRecord:
        for task in self.record.tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"unknown task {task_id!r}")

    def has_task(self, task_id: str) -> bool:
        return any(task.id == task_id for task in self.record.tasks)

    def emit(
        self, type_: str, message: str = "", task_id: str | None = None, **data: Any
    ) -> JobEvent:
        event = JobEvent(
            seq=len(self.events),
            type=type_,
            job_id=self.id,
            task_id=task_id,
            message=message,
            data=data,
        )
        self.events.append(event)
        return event
