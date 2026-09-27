"""ClaudeCodeProvider: command shape, output parsing, and a fake `claude` executable."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from vectron.config import Settings
from vectron.llm import create_provider
from vectron.llm.base import LLMError
from vectron.llm.claude_code_provider import ClaudeCodeProvider, parse_result

SCHEMA = {"type": "object", "properties": {"answer": {"type": "integer"}}}


def ok(**extra: object) -> bytes:
    payload = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": '{"answer": 42}',
        "structured_output": {"answer": 42},
        "usage": {"input_tokens": 5, "cache_read_input_tokens": 100, "output_tokens": 7},
        "modelUsage": {"claude-sonnet-5": {}},
        **extra,
    }
    return json.dumps(payload).encode()


def test_command_disables_tools_and_user_settings() -> None:
    command = ClaudeCodeProvider("/bin/claude", model="claude-opus-5").command("sys", SCHEMA)
    assert command[:2] == ["/bin/claude", "-p"]
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--setting-sources") + 1] == ""
    assert json.loads(command[command.index("--json-schema") + 1]) == SCHEMA
    assert command[command.index("--model") + 1] == "claude-opus-5"
    assert "--model" not in ClaudeCodeProvider("/bin/claude").command("sys", SCHEMA)


def test_parse_success_prefers_structured_output() -> None:
    result = parse_result(ok(), b"", 0)
    assert result.data == {"answer": 42}
    assert result.model == "claude-sonnet-5"
    assert (result.input_tokens, result.output_tokens) == (105, 7)
    fallback = parse_result(ok(structured_output=None), b"", 0)
    assert fallback.data == {"answer": 42}


@pytest.mark.parametrize(
    ("stdout", "message"),
    [
        (b"", "Is it installed and logged in"),
        (b"Not logged in", "Is it installed and logged in"),
        (ok(is_error=True, result="usage limit reached"), "usage limit"),
        (ok(structured_output=None, result="plain prose"), "no structured output"),
    ],
)
def test_parse_failures(stdout: bytes, message: str) -> None:
    with pytest.raises(LLMError, match=message):
        parse_result(stdout, b"", 1)


async def test_runs_the_cli_with_prompt_on_stdin(tmp_path: Path) -> None:
    received = tmp_path / "stdin.txt"
    fake = tmp_path / "claude"
    fake.write_text(f"#!/bin/sh\ncat > {received}\necho '{ok().decode()}'\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    provider = ClaudeCodeProvider(str(fake))
    result = await provider.generate_json(system="sys", prompt="build a drone", schema=SCHEMA)
    assert result.data == {"answer": 42}
    assert received.read_text() == "build a drone"


async def test_missing_binary_is_an_llm_error(tmp_path: Path) -> None:
    provider = ClaudeCodeProvider(str(tmp_path / "nope"))
    with pytest.raises(LLMError, match="could not start"):
        await provider.generate_json(system="s", prompt="p", schema=SCHEMA)


def test_selection_falls_back_when_claude_is_not_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    provider = create_provider(Settings(data_dir=tmp_path, llm_provider="claude-code"))
    assert not provider.enabled and "claude" in provider.detail
