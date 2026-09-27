"""The Factory: one object that wires catalog, agents, LLM and job storage together.

Both the HTTP API and the CLI drive builds through this class.
"""

from __future__ import annotations

import asyncio
import uuid

from vectron.agents import default_agents
from vectron.blueprints.catalog import BlueprintCatalog
from vectron.codegen.python.generator import PythonTarget
from vectron.config import Settings
from vectron.domain.jobs import BuildRequest, JobRecord, LLMInfo
from vectron.llm import LLMProvider, create_provider
from vectron.orchestration import Job, Orchestrator
from vectron.orchestration.workspace import Workspace


class Factory:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: LLMProvider | None = None,
        catalog: BlueprintCatalog | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.catalog = catalog or BlueprintCatalog.load(self.settings.blueprint_dirs)
        self.llm = llm or create_provider(self.settings)
        self.target = PythonTarget()
        self.orchestrator = Orchestrator(
            default_agents(),
            llm=self.llm,
            catalog=self.catalog,
            target=self.target,
            settings=self.settings,
        )
        self._jobs: dict[str, Job] = {}

    # -- jobs ---------------------------------------------------------------

    def create_job(self, request: BuildRequest) -> Job:
        """Validate the request up front (so the API can answer 4xx) and register a job."""
        if request.blueprint_id:
            self.catalog.get(request.blueprint_id).resolve_options(request.options)
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        record = JobRecord(
            id=job_id,
            request=request,
            llm=LLMInfo(provider=self.llm.name, model=self.llm.model if self.llm.enabled else None),
        )
        job = Job(record, Workspace(self.settings.data_dir / "jobs" / job_id))
        self._jobs[job_id] = job
        job.emit("job.queued", "Work order received")
        return job

    def submit(self, request: BuildRequest) -> Job:
        """Create a job and run it in the background on the current event loop."""
        job = self.create_job(request)
        job.runner = asyncio.create_task(self.orchestrator.run(job), name=job.id)
        return job

    async def build(self, request: BuildRequest) -> Job:
        """Create a job and run it to completion (CLI and tests)."""
        job = self.create_job(request)
        await self.orchestrator.run(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.record.created_at, reverse=True)

    async def shutdown(self) -> None:
        runners = [j.runner for j in self._jobs.values() if j.runner and not j.runner.done()]
        for runner in runners:
            runner.cancel()
        await asyncio.gather(*runners, return_exceptions=True)
