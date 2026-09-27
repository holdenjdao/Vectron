"""Agent contract: one role, one ``run`` coroutine, results that can spawn more agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from .context import RunContext


@dataclass(frozen=True)
class TaskSpec:
    """A request for another agent to do some work (the unit of delegation)."""

    id: str
    role: str
    title: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    """Task ids that must succeed first. The spawning task is always an implicit dependency."""


@dataclass(frozen=True)
class AgentResult:
    summary: str
    spawn: tuple[TaskSpec, ...] = ()


class Agent(ABC):
    """Subclasses set ``role`` (routing key), ``display_name`` and ``description``."""

    role: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str]

    @abstractmethod
    async def run(self, ctx: RunContext) -> AgentResult: ...
