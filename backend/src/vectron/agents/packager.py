"""Quartermaster: writes the README and manifest, then seals the downloadable bundle."""

from __future__ import annotations

import json

from vectron import __version__
from vectron.codegen.files import GeneratedFile
from vectron.domain.jobs import ArtifactKind, utcnow
from vectron.orchestration import Agent, AgentResult, RunContext


def render_tree(paths: list[str]) -> str:
    """A compact ``tree``-style listing, folders first."""
    root: dict[str, dict] = {}
    for path in paths:
        node = root
        for part in path.split("/"):
            node = node.setdefault(part, {})

    lines: list[str] = []

    def walk(node: dict[str, dict], prefix: str) -> None:
        entries = sorted(node.items(), key=lambda item: (not item[1], item[0]))
        for index, (name, child) in enumerate(entries):
            last = index == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{name}{'/' if child else ''}")
            if child:
                walk(child, prefix + ("    " if last else "│   "))

    walk(root, "")
    return "\n".join(lines)


class PackagerAgent(Agent):
    role = "packager"
    display_name = "Quartermaster"
    description = "Documents, manifests and bundles the build for download."

    async def run(self, ctx: RunContext) -> AgentResult:
        spec, record = ctx.spec, ctx.job.record
        manifest_path, readme_path = "vectron.manifest.json", "README.md"
        paths = sorted({a.path for a in record.artifacts} | {manifest_path, readme_path})
        ctx.save(
            ctx.target.readme(
                spec,
                job_id=record.id,
                generated_at=utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                module_builds=record.modules,
                notes=ctx.job.board.architect_notes,
                layout=render_tree(paths),
            )
        )
        ctx.save(self._manifest(ctx, manifest_path))

        files = [a.path for a in record.artifacts]
        data = ctx.job.workspace.build_zip(top=spec.id, paths=files)
        record.bundle = ctx.job.workspace.save_bundle(f"{spec.id}.zip", data, len(files))
        return AgentResult(
            summary=f"{record.bundle.filename}: {len(files)} files, {len(data) / 1024:.1f} KiB"
        )

    def _manifest(self, ctx: RunContext, path: str) -> GeneratedFile:
        record, board = ctx.job.record, ctx.job.board
        manifest = {
            "vectron": __version__,
            "job": record.id,
            "created_at": record.created_at.isoformat(),
            "blueprint": (
                {
                    "id": board.blueprint.id,
                    "designation": board.blueprint.designation,
                    "options": board.options,
                }
                if board.blueprint
                else {"id": None, "designed_from_brief": True}
            ),
            "brief": record.request.brief,
            "llm": {**record.llm.model_dump(), **record.usage.model_dump()},
            "modules": [
                {"id": b.id, "class": b.class_name, "path": b.path, "provenance": b.provenance}
                for b in record.modules
            ],
            "inspection": record.inspection.counts if record.inspection else None,
            "artifacts": [
                {"path": a.path, "kind": a.kind.value, "size": a.size, "sha256": a.sha256}
                for a in sorted(record.artifacts, key=lambda a: a.path)
                if a.path != path
            ],
        }
        return GeneratedFile(
            path,
            json.dumps(manifest, indent=2) + "\n",
            ArtifactKind.CONFIG,
            "application/json",
            "Build manifest",
            "Provenance, options and SHA-256 of every artifact in the bundle.",
        )
