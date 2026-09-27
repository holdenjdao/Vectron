"""Language-model providers."""

from __future__ import annotations

import logging

from vectron.config import Settings

from .base import LLMError, LLMProvider, LLMResult
from .offline import OfflineProvider

__all__ = ["LLMError", "LLMProvider", "LLMResult", "OfflineProvider", "create_provider"]

log = logging.getLogger(__name__)


def create_provider(settings: Settings) -> LLMProvider:
    """Build the provider named by ``VECTRON_LLM_PROVIDER`` (default: offline)."""
    choice = settings.llm_provider.lower()
    if choice in ("", "offline", "none"):
        return OfflineProvider()
    if choice in ("anthropic", "claude"):
        try:
            from .anthropic_provider import AnthropicProvider

            return AnthropicProvider(model=settings.model, effort=settings.effort)
        except Exception as exc:  # misconfiguration should not stop the factory
            log.warning("Anthropic provider unavailable, using offline mode: %s", exc)
            return OfflineProvider(reason=f"(Anthropic provider failed to start: {exc})")
    return OfflineProvider(reason=f"(unknown VECTRON_LLM_PROVIDER {settings.llm_provider!r})")
