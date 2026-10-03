"""Test doubles."""

from __future__ import annotations

from typing import Any

from vectron.llm.base import LLMError, LLMProvider, LLMResult


class ScriptedLLM(LLMProvider):
    """Test double: answers by the first keyword found in the system prompt."""

    name = "scripted"
    model = "scripted-model"

    def __init__(self, answers: dict[str, dict[str, Any] | Exception]) -> None:
        self.answers = answers
        self.calls: list[str] = []

    @property
    def enabled(self) -> bool:
        return True

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        effort: str | None = None,
        max_tokens: int = 32_000,
    ) -> LLMResult:
        for key, answer in self.answers.items():
            if key in system:
                self.calls.append(key)
                if isinstance(answer, Exception):
                    raise answer
                return LLMResult(data=answer, model=self.model, input_tokens=100, output_tokens=50)
        raise LLMError("no scripted answer")
