"""Runtime settings, read from ``VECTRON_*`` environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("VECTRON_DATA_DIR", ".vectron")))
    """Where job workspaces and bundles are written."""
    llm_provider: str = field(default_factory=lambda: _env("VECTRON_LLM_PROVIDER", "offline"))
    """``offline`` (deterministic, no network) or ``anthropic`` (Claude)."""
    model: str = field(default_factory=lambda: _env("VECTRON_MODEL", "claude-opus-5"))
    effort: str = field(default_factory=lambda: _env("VECTRON_EFFORT", "medium"))
    """Claude effort level: low, medium, high, xhigh or max."""
    max_concurrency: int = field(default_factory=lambda: int(_env("VECTRON_MAX_CONCURRENCY", "4")))
    """Upper bound on agents running at once (keeps LLM rate limits in check)."""
    pacing_s: float = field(default_factory=lambda: float(_env("VECTRON_PACING_SECONDS", "0")))
    """Artificial delay per task so demos can watch the assembly line; 0 disables."""
    banner: str = field(default_factory=lambda: _env("VECTRON_BANNER", "UNCLASSIFIED"))
    static_dir: Path | None = field(
        default_factory=lambda: Path(p) if (p := _env("VECTRON_STATIC_DIR", "")) else None
    )
    """Built frontend to serve at ``/``; defaults to ``frontend/dist`` when it exists."""
    blueprint_dirs: tuple[Path, ...] = field(
        default_factory=lambda: tuple(
            Path(p) for p in _env("VECTRON_BLUEPRINT_DIRS", "").split(os.pathsep) if p
        )
    )
