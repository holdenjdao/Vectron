"""The live job object: serializable record, event log, workspace and shared blackboard."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from vectron.domain.blueprint import Blueprint
from vectron.domain.jobs import JobEvent, JobRecord, TaskRecord
from vectron.domain.spec import SystemSpec

from .events import EventLog
from .workspace import Workspace


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
