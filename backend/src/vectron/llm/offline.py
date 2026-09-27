"""Offline provider: no model at all. Every agent uses its deterministic path."""

from __future__ import annotations

from typing import Any

from .base import LLMError, LLMProvider, LLMResult


class OfflineProvider(LLMProvider):
    name = "offline"

    def __init__(self, reason: str = "") -> None:
        self._reason = reason

    @property
    def enabled(self) -> bool:
        return False

    @property
    def detail(self) -> str:
        base = "Deterministic offline mode: blueprints, parts library and stubs; no model calls."
        return f"{base} {self._reason}".strip()

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        effort: str | None = None,
        max_tokens: int = 32_000,
    ) -> LLMResult:
        raise LLMError("no language model configured (offline mode)")
