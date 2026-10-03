"""AnthropicProvider request shaping and response handling, against a fake SDK client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from vectron.config import Settings
from vectron.llm import create_provider
from vectron.llm.anthropic_provider import FALLBACK_BETA, AnthropicProvider
from vectron.llm.base import LLMError


class FakeStream:
    def __init__(self, message: Any) -> None:
        self.message = message

    async def __aenter__(self) -> FakeStream:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get_final_message(self) -> Any:
        return self.message


class FakeClient:
    def __init__(self, text: str = '{"answer": 42}', stop_reason: str = "end_turn") -> None:
        self.requests: list[dict[str, Any]] = []
        message = SimpleNamespace(
            stop_reason=stop_reason,
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text=text),
            ],
            model="claude-opus-5",
            usage=SimpleNamespace(input_tokens=120, output_tokens=30),
        )

        def stream(**kwargs: Any) -> FakeStream:
            self.requests.append(kwargs)
            return FakeStream(message)

        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=stream))


SCHEMA = {"type": "object", "properties": {"answer": {"type": "integer"}}}


async def test_structured_request_with_default_fallbacks() -> None:
    client = FakeClient()
    provider = AnthropicProvider("claude-opus-5", effort="medium", client=client)  # type: ignore[arg-type]
    result = await provider.generate_json(system="sys", prompt="hi", schema=SCHEMA)
    assert result.data == {"answer": 42}
    assert (result.input_tokens, result.output_tokens) == (120, 30)
    request = client.requests[0]
    assert request["model"] == "claude-opus-5"
    assert request["output_config"] == {
        "format": {"type": "json_schema", "schema": SCHEMA},
        "effort": "medium",
    }
    assert request["betas"] == [FALLBACK_BETA] and request["fallbacks"] == "default"
    assert "temperature" not in request and "thinking" not in request


async def test_models_without_fallback_support_omit_it() -> None:
    client = FakeClient()
    provider = AnthropicProvider("claude-sonnet-5", effort="", client=client)  # type: ignore[arg-type]
    await provider.generate_json(system="s", prompt="p", schema=SCHEMA, effort="low")
    request = client.requests[0]
    assert "fallbacks" not in request and "betas" not in request
    assert request["output_config"]["effort"] == "low"


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (FakeClient(stop_reason="refusal"), "declined"),
        (FakeClient(stop_reason="max_tokens"), "truncated"),
        (FakeClient(text="not json"), "not valid JSON"),
        (FakeClient(text="[1, 2]"), "not an object"),
    ],
)
async def test_unusable_responses_raise(client: FakeClient, message: str) -> None:
    provider = AnthropicProvider("claude-opus-5", client=client)  # type: ignore[arg-type]
    with pytest.raises(LLMError, match=message):
        await provider.generate_json(system="s", prompt="p", schema=SCHEMA)


def test_provider_selection(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    offline = create_provider(Settings(data_dir=tmp_path, llm_provider="offline"))
    assert not offline.enabled
    no_key = create_provider(Settings(data_dir=tmp_path, llm_provider="anthropic"))
    assert not no_key.enabled and "ANTHROPIC_API_KEY" in no_key.detail

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    claude = create_provider(Settings(data_dir=tmp_path, llm_provider="anthropic"))
    assert claude.enabled and claude.model == "claude-opus-5"
    unknown = create_provider(Settings(data_dir=tmp_path, llm_provider="nope"))
    assert not unknown.enabled and "nope" in unknown.detail
