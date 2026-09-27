"""Claude through the local Claude Code CLI (``claude -p``), using your Claude subscription.

No API key: requests run under whatever account Claude Code is logged in with on
this machine and count against that subscription's usage limits. Intended for
personal, local use; a hosted multi-user deployment should use the API provider.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from typing import Any

from .base import LLMError, LLMProvider, LLMResult

CALL_TIMEOUT_S = 600.0


class ClaudeCodeProvider(LLMProvider):
    name = "claude-code"

    def __init__(self, binary: str, model: str | None = None) -> None:
        self.binary = binary
        self.model = model

    @classmethod
    def find_binary(cls) -> str | None:
        return shutil.which("claude")

    @property
    def enabled(self) -> bool:
        return True

    @property
    def detail(self) -> str:
        model = self.model or "your Claude Code default model"
        return f"Claude via your Claude subscription (Claude Code CLI, {model})."

    def command(self, system: str, schema: dict[str, Any]) -> list[str]:
        command = [
            self.binary,
            "-p",
            "--output-format", "json",
            "--json-schema", json.dumps(schema),
            "--system-prompt", system,
            "--tools", "",  # pure text generation: no file, shell or web access
            "--setting-sources", "",  # ignore the user's hooks and project settings
            "--no-session-persistence",
        ]  # fmt: skip
        if self.model:
            command += ["--model", self.model]
        return command

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        effort: str | None = None,
        max_tokens: int = 32_000,
    ) -> LLMResult:
        # Run from an empty directory so no project CLAUDE.md is picked up.
        with tempfile.TemporaryDirectory(prefix="vectron-claude-") as workdir:
            try:
                process = await asyncio.create_subprocess_exec(
                    *self.command(system, schema),
                    cwd=workdir,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except OSError as exc:
                raise LLMError(f"could not start Claude Code ({self.binary}): {exc}") from exc
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(prompt.encode("utf-8")), CALL_TIMEOUT_S
                )
            except TimeoutError as exc:
                process.kill()
                await process.wait()
                raise LLMError(f"Claude Code did not answer within {CALL_TIMEOUT_S:.0f}s") from exc
        return parse_result(stdout, stderr, process.returncode)


def parse_result(stdout: bytes, stderr: bytes, returncode: int | None) -> LLMResult:
    """Turn ``claude -p --output-format json`` output into an LLMResult."""
    try:
        payload = json.loads(stdout.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        hint = (stderr or stdout).decode("utf-8", "replace").strip()[:300]
        raise LLMError(
            f"Claude Code failed (exit {returncode}): {hint or 'no output'}. "
            "Is it installed and logged in? Run `claude` once in a terminal to check."
        ) from None
    if (
        not isinstance(payload, dict)
        or payload.get("is_error")
        or payload.get("subtype") != "success"
    ):
        message = payload.get("result") if isinstance(payload, dict) else None
        raise LLMError(f"Claude Code reported an error: {str(message or payload)[:300]}")
    data = payload.get("structured_output")
    if data is None:
        try:
            data = json.loads(payload.get("result") or "")
        except json.JSONDecodeError as exc:
            raise LLMError("Claude Code returned no structured output") from exc
    if not isinstance(data, dict):
        raise LLMError("Claude Code's structured output was not a JSON object")
    usage = payload.get("usage") or {}
    models = list((payload.get("modelUsage") or {}).keys())
    return LLMResult(
        data=data,
        model=models[0] if models else "claude-code",
        input_tokens=int(usage.get("input_tokens", 0))
        + int(usage.get("cache_read_input_tokens", 0))
        + int(usage.get("cache_creation_input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )
