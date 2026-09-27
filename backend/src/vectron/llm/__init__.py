"""Language-model providers."""

from __future__ import annotations

import logging
import os

from vectron.config import Settings

from .base import LLMError, LLMProvider, LLMResult
from .offline import OfflineProvider

__all__ = ["LLMError", "LLMProvider", "LLMResult", "OfflineProvider", "create_provider"]

log = logging.getLogger(__name__)


def create_provider(settings: Settings) -> LLMProvider:
    """Build the provider named by ``VECTRON_LLM_PROVIDER``: offline, claude-code or anthropic."""
    choice = settings.llm_provider.lower()
    if choice in ("", "offline", "none"):
        return OfflineProvider()
    if choice in ("anthropic", "claude"):
        try:
            from .anthropic_provider import AnthropicProvider

            provider = AnthropicProvider(model=settings.model, effort=settings.effort)
        except Exception as exc:  # misconfiguration should not stop the factory
            log.warning("Anthropic provider unavailable, using offline mode: %s", exc)
            return OfflineProvider(reason=f"(Anthropic provider failed to start: {exc})")
        if not provider.has_credentials:
            log.warning("VECTRON_LLM_PROVIDER=anthropic but no Anthropic credentials found")
            return OfflineProvider(
                reason="(Claude requested but no credentials found: set ANTHROPIC_API_KEY "
                "or run `ant auth login`.)"
            )
        return provider
    if choice in ("claude-code", "claude_code", "subscription"):
        from .claude_code_provider import ClaudeCodeProvider

        binary = ClaudeCodeProvider.find_binary()
        if binary is None:
            return OfflineProvider(
                reason="(Claude Code requested but the `claude` command was not found: install it "
                "with `npm install -g @anthropic-ai/claude-code` and run `claude` once to log in.)"
            )
        return ClaudeCodeProvider(binary, model=os.environ.get("VECTRON_MODEL") or None)
    return OfflineProvider(reason=f"(unknown VECTRON_LLM_PROVIDER {settings.llm_provider!r})")
