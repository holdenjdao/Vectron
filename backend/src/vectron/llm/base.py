"""The provider interface agents use to reach a language model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LLMError(RuntimeError):
    """The model call failed or returned unusable output. Agents fall back on this."""


@dataclass(frozen=True)
class LLMResult:
    data: dict[str, Any]
    """Parsed JSON matching the requested schema."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    """A source of structured model output.

    Agents only ever ask for JSON that matches a schema; they validate the result
    themselves and fall back to deterministic behaviour on any :class:`LLMError`.
    """

    name: str = "provider"
    model: str | None = None

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """False when agents should not attempt model calls at all."""

    @property
    def detail(self) -> str:
        return self.name

    @abstractmethod
    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        effort: str | None = None,
        max_tokens: int = 32_000,
    ) -> LLMResult:
        """Return model output conforming to ``schema`` or raise :class:`LLMError`."""
