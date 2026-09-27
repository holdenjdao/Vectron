"""The unit of output every renderer produces."""

from __future__ import annotations

from dataclasses import dataclass

from vectron.domain.jobs import ArtifactKind


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    """POSIX path relative to the generated project root."""
    content: str | bytes
    kind: ArtifactKind
    media_type: str
    title: str
    description: str = ""
    module_id: str | None = None


class CodegenError(RuntimeError):
    """A template or renderer produced invalid output."""
