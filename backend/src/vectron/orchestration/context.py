"""What an agent can see and do while running one task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vectron.blueprints.catalog import BlueprintCatalog
from vectron.codegen.files import GeneratedFile
from vectron.codegen.python.generator import PythonTarget
from vectron.config import Settings
from vectron.domain.jobs import Artifact, TaskRecord
from vectron.domain.spec import SystemSpec
from vectron.llm.base import LLMProvider, LLMResult

from .job import Job


class AgentError(RuntimeError):
    """An agent could not complete its task; the message is shown to the user."""


@dataclass
class RunContext:
    job: Job
    task: TaskRecord
    llm: LLMProvider
    catalog: BlueprintCatalog
    target: PythonTarget
    settings: Settings

    @property
    def spec(self) -> SystemSpec:
        if self.job.board.spec is None:
            raise AgentError("no system spec yet: the Architect has not run")
        return self.job.board.spec

    @property
    def params(self) -> dict[str, Any]:
        return self.task.params

    def log(self, message: str, **data: Any) -> None:
        self.job.emit("task.log", message, task_id=self.task.id, **data)

    def save(self, file: GeneratedFile) -> Artifact:
        """Write a file into the job workspace and register it as an artifact."""
        size, sha256 = self.job.workspace.write(file.path, file.content)
        artifact = Artifact(
            path=file.path,
            kind=file.kind,
            media_type=file.media_type,
            title=file.title,
            description=file.description,
            size=size,
            sha256=sha256,
            module_id=file.module_id,
            producer=self.task.id,
        )
        artifacts = self.job.record.artifacts
        artifacts[:] = [a for a in artifacts if a.path != file.path]
        artifacts.append(artifact)
        self.job.emit(
            "artifact.created",
            f"{file.path} ({size:,} bytes)",
            task_id=self.task.id,
            path=file.path,
            kind=file.kind.value,
        )
        return artifact

    async def ask_llm(
        self,
        *,
        purpose: str,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        effort: str | None = None,
    ) -> LLMResult:
        """Call the model and account for usage. Raises LLMError on any failure."""
        self.log(f"Consulting {self.llm.model or self.llm.name}: {purpose}")
        result = await self.llm.generate_json(
            system=system, prompt=prompt, schema=schema, effort=effort
        )
        usage = self.job.record.usage
        usage.calls += 1
        usage.input_tokens += result.input_tokens
        usage.output_tokens += result.output_tokens
        self.log(
            f"{result.model} answered ({result.input_tokens:,} in / "
            f"{result.output_tokens:,} out tokens)"
        )
        return result
