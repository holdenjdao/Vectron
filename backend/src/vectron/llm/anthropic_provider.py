"""Claude via the Anthropic API, with structured (JSON-schema) outputs."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from .base import LLMError, LLMProvider, LLMResult

# Models that accept server-side refusal fallbacks (``fallbacks: "default"``).
FALLBACK_MODELS = frozenset(
    {"claude-opus-5", "claude-opus-5-5", "claude-fable-5", "claude-fable-5-1"}
)
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self, model: str, effort: str = "medium", client: anthropic.AsyncAnthropic | None = None
    ) -> None:
        # Credentials resolve the SDK's usual way: ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN
        # or an `ant auth login` profile.
        self.client = client or anthropic.AsyncAnthropic()
        self.model = model
        self.effort = effort

    @property
    def enabled(self) -> bool:
        return True

    @property
    def has_credentials(self) -> bool:
        client = self.client
        return any(getattr(client, attr, None) for attr in ("api_key", "auth_token", "credentials"))

    @property
    def detail(self) -> str:
        return f"Claude via the Anthropic API ({self.model}, effort {self.effort or 'default'})."

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        effort: str | None = None,
        max_tokens: int = 32_000,
    ) -> LLMResult:
        output_config: dict[str, Any] = {"format": {"type": "json_schema", "schema": schema}}
        if effort or self.effort:
            output_config["effort"] = effort or self.effort
        extra: dict[str, Any] = {}
        if self.model in FALLBACK_MODELS:
            # Re-run a request declined by a safety classifier on Anthropic's recommended
            # fallback model instead of failing the build step.
            extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        try:
            async with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config=output_config,  # type: ignore[arg-type]
                **extra,
            ) as stream:
                message = await stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"could not reach the Claude API: {exc}") from exc
        except anthropic.AnthropicError as exc:
            raise LLMError(f"Claude client error: {exc}") from exc

        if message.stop_reason == "refusal":
            raise LLMError("Claude declined this request")
        if message.stop_reason == "max_tokens":
            raise LLMError(f"response truncated at max_tokens={max_tokens}")
        text = next((block.text for block in message.content if block.type == "text"), None)
        if text is None:
            raise LLMError("response contained no text block")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"response was not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise LLMError("response JSON was not an object")
        usage = message.usage
        return LLMResult(
            data=data,
            model=message.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
