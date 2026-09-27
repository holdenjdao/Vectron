"""The orchestrator: runs a job's task graph, letting agents delegate to other agents.

A job starts as a single task for the Commander. Each finished task may spawn
new tasks (its ``AgentResult.spawn``); those depend implicitly on the task that
spawned them, plus any explicit ``depends_on``. Ready tasks run concurrently up
to ``max_concurrency``. A failed task causes its dependents to be skipped, and
the job fails if any task fails.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from collections.abc import Mapping

from vectron.blueprints.catalog import BlueprintCatalog
from vectron.codegen.python.generator import PythonTarget
from vectron.config import Settings
from vectron.domain.jobs import JobStatus, TaskRecord, TaskStatus, utcnow
from vectron.llm.base import LLMProvider

from .agent import Agent, AgentResult, TaskSpec
from .context import AgentError, RunContext
from .job import Job

log = logging.getLogger(__name__)

ROOT_TASK_ID = "plan"


class Orchestrator:
    def __init__(
        self,
        agents: Mapping[str, Agent],
        *,
        llm: LLMProvider,
        catalog: BlueprintCatalog,
        target: PythonTarget,
        settings: Settings,
    ) -> None:
        self.agents = agents
        self.llm = llm
        self.catalog = catalog
        self.target = target
        self.settings = settings

    async def run(self, job: Job) -> None:
        record = job.record
        record.status = JobStatus.RUNNING
        record.started_at = utcnow()
        job.emit("job.started", "Factory floor engaged")
        self._enqueue(
            job, TaskSpec(ROOT_TASK_ID, "planner", "Interpret the request and plan"), None
        )

        running: dict[asyncio.Task[AgentResult], TaskRecord] = {}
        try:
            while True:
                self._skip_blocked(job)
                for task in self._ready(job):
                    if len(running) >= max(1, self.settings.max_concurrency):
                        break
                    running[asyncio.create_task(self._execute(job, task))] = task
                if not running:
                    self._skip_unreachable(job)
                    break
                done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
                for future in done:
                    self._finish(job, running.pop(future), future)
        except asyncio.CancelledError:
            for future, task in running.items():
                future.cancel()
                self._close_task(job, task, TaskStatus.FAILED, error="cancelled")
            self._finalize(job, cancelled=True)
            raise
        self._finalize(job)

    # -- graph bookkeeping --------------------------------------------------

    def _enqueue(self, job: Job, spec: TaskSpec, parent: TaskRecord | None) -> None:
        agent = self.agents.get(spec.role)
        if agent is None:
            raise AgentError(f"no agent registered for role {spec.role!r}")
        if job.has_task(spec.id):
            raise AgentError(f"duplicate task id {spec.id!r}")
        depends_on = list(spec.depends_on)
        if parent is not None and parent.id not in depends_on:
            depends_on.insert(0, parent.id)
        task = TaskRecord(
            id=spec.id,
            role=spec.role,
            agent=agent.display_name,
            title=spec.title,
            parent_id=parent.id if parent else None,
            depends_on=depends_on,
            params=dict(spec.params),
        )
        job.record.tasks.append(task)
        job.emit("task.queued", task.title, task_id=task.id, role=task.role, agent=task.agent)

    def _ready(self, job: Job) -> list[TaskRecord]:
        statuses = {t.id: t.status for t in job.record.tasks}
        return [
            task
            for task in job.record.tasks
            if task.status is TaskStatus.PENDING
            and all(statuses.get(dep) is TaskStatus.SUCCEEDED for dep in task.depends_on)
        ]

    def _skip_blocked(self, job: Job) -> None:
        """Skip pending tasks whose dependencies failed or were skipped (cascading)."""
        changed = True
        while changed:
            changed = False
            statuses = {t.id: t.status for t in job.record.tasks}
            for task in job.record.tasks:
                if task.status is not TaskStatus.PENDING:
                    continue
                blocked = [
                    d
                    for d in task.depends_on
                    if statuses.get(d) in (TaskStatus.FAILED, TaskStatus.SKIPPED)
                ]
                if blocked:
                    self._close_task(
                        job, task, TaskStatus.SKIPPED, error=f"blocked by {blocked[0]}"
                    )
                    changed = True

    def _skip_unreachable(self, job: Job) -> None:
        for task in job.record.tasks:
            if task.status is TaskStatus.PENDING:
                self._close_task(job, task, TaskStatus.SKIPPED, error="unresolvable dependency")

    # -- execution -----------------------------------------------------------

    async def _execute(self, job: Job, task: TaskRecord) -> AgentResult:
        task.status = TaskStatus.RUNNING
        task.started_at = utcnow()
        job.emit("task.started", task.title, task_id=task.id)
        if self.settings.pacing_s > 0:
            await asyncio.sleep(self.settings.pacing_s)
        ctx = RunContext(
            job=job,
            task=task,
            llm=self.llm,
            catalog=self.catalog,
            target=self.target,
            settings=self.settings,
        )
        return await self.agents[task.role].run(ctx)

    def _finish(self, job: Job, task: TaskRecord, future: asyncio.Task[AgentResult]) -> None:
        error = future.exception()
        if error is not None:
            if not isinstance(error, AgentError):
                log.error(
                    "task %s crashed:\n%s",
                    task.id,
                    "".join(traceback.format_exception(error)),
                )
            self._close_task(job, task, TaskStatus.FAILED, error=str(error) or type(error).__name__)
            return
        result = future.result()
        task.summary = result.summary
        try:
            for spec in result.spawn:
                self._enqueue(job, spec, parent=task)
        except AgentError as exc:
            self._close_task(job, task, TaskStatus.FAILED, error=str(exc))
            return
        self._close_task(job, task, TaskStatus.SUCCEEDED)
        if result.spawn:
            names = ", ".join(sorted({self.agents[s.role].display_name for s in result.spawn}))
            job.emit(
                "task.log",
                f"Delegated {len(result.spawn)} task(s) to: {names}",
                task_id=task.id,
            )

    def _close_task(
        self, job: Job, task: TaskRecord, status: TaskStatus, error: str | None = None
    ) -> None:
        task.status = status
        task.error = error
        task.finished_at = utcnow()
        message = task.summary if status is TaskStatus.SUCCEEDED else (error or status.value)
        job.emit(f"task.{status.value}", message, task_id=task.id)

    def _finalize(self, job: Job, cancelled: bool = False) -> None:
        record = job.record
        record.finished_at = utcnow()
        failed = [t for t in record.tasks if t.status is TaskStatus.FAILED]
        if cancelled or failed:
            record.status = JobStatus.FAILED
            record.error = "cancelled" if cancelled else f"{failed[0].agent}: {failed[0].error}"
            job.emit("job.failed", record.error)
        else:
            record.status = JobStatus.SUCCEEDED
            job.emit("job.succeeded", f"Build complete: {len(record.artifacts)} artifacts")
        job.events.close()
