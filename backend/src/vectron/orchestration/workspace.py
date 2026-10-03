"""A job's working directory: the generated project plus its zip bundles."""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath

from vectron.domain.jobs import BundleInfo

# Fixed timestamp inside zips so identical builds produce identical bundles.
_ZIP_DATE = (2020, 1, 1, 0, 0, 0)


def safe_relative_path(path: str) -> PurePosixPath:
    """Reject absolute paths, ``..`` segments and other escapes from the project root."""
    posix = PurePosixPath(path)
    if not path or posix.is_absolute() or any(part in ("", ".", "..") for part in posix.parts):
        raise ValueError(f"unsafe artifact path: {path!r}")
    if "\\" in path or ":" in path:
        raise ValueError(f"unsafe artifact path: {path!r}")
    return posix


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.project = root / "project"
        self.project.mkdir(parents=True, exist_ok=True)

    def write(self, path: str, content: str | bytes) -> tuple[int, str]:
        """Write a project file; returns ``(size, sha256)``."""
        data = content.encode("utf-8") if isinstance(content, str) else content
        target = self.project / safe_relative_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return len(data), hashlib.sha256(data).hexdigest()

    def read(self, path: str) -> bytes:
        return (self.project / safe_relative_path(path)).read_bytes()

    def build_zip(
        self,
        top: str,
        paths: Iterable[str],
        extra: Mapping[str, str | bytes] | None = None,
    ) -> bytes:
        """Zip the given project paths (plus in-memory extras) under a ``top/`` folder."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            entries: dict[str, bytes] = {p: self.read(p) for p in paths}
            for name, content in (extra or {}).items():
                safe_relative_path(name)
                entries[name] = content.encode("utf-8") if isinstance(content, str) else content
            for name in sorted(entries):
                info = zipfile.ZipInfo(f"{top}/{name}", date_time=_ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, entries[name])
        return buffer.getvalue()

    def save_bundle(self, filename: str, data: bytes, file_count: int) -> BundleInfo:
        (self.root / filename).write_bytes(data)
        return BundleInfo(
            filename=filename,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            file_count=file_count,
        )

    def bundle_path(self, filename: str) -> Path:
        return self.root / safe_relative_path(filename)
