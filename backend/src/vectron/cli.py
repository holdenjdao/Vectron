"""Command line: ``vectron serve | blueprints | parts | build``."""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
import zipfile
from pathlib import Path

from vectron import __version__
from vectron.domain.jobs import BuildRequest, JobEvent, JobStatus

COLORS = {"succeeded": "32", "failed": "31", "skipped": "90", "started": "36", "artifact": "34"}
# Source files whose edits should restart `vectron serve --reload`: code, templates,
# blueprints and agent prompts.
RELOAD_PATTERNS = ("*.py", "*.j2", "*.yaml", "*.md")


def _paint(text: str, code: str | None) -> str:
    return f"\033[{code}m{text}\033[0m" if code and sys.stdout.isatty() else text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vectron", description="Vectron software factory")
    parser.add_argument("--version", action="version", version=f"vectron {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the API and web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="restart on code changes")

    commands.add_parser("blueprints", help="list the blueprint catalog")
    commands.add_parser("parts", help="list the parts library")

    build = commands.add_parser("build", help="run a build and write the project to disk")
    build.add_argument("blueprint", nargs="?", help="blueprint id (omit to plan from --brief)")
    build.add_argument("--brief", default="", help="free-text mission brief")
    build.add_argument(
        "--option", "-o", action="append", default=[], metavar="KEY=VALUE", help="blueprint option"
    )
    build.add_argument("--out", type=Path, default=Path("."), help="output directory")

    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn

        # With --reload, watch only Vectron's own source. Builds write generated
        # projects (including .py files) under the data directory, and a reload
        # there would restart the server and cancel the build in progress.
        uvicorn.run(
            "vectron.api.app:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
            reload_dirs=[str(Path(__file__).resolve().parent)] if args.reload else None,
            reload_includes=list(RELOAD_PATTERNS) if args.reload else None,
        )
        return 0
    if args.command == "blueprints":
        return _list_blueprints()
    if args.command == "parts":
        return _list_parts()
    return asyncio.run(_build(args))


def _list_blueprints() -> int:
    from vectron.blueprints.catalog import BlueprintCatalog

    for blueprint in BlueprintCatalog.load().list():
        stats = blueprint.stats
        print(f"{blueprint.id:<24} {blueprint.designation:<10} {blueprint.name}")
        print(f"{'':<24} {stats['subsystems']} subsystems, {stats['modules']} modules")
        for option in blueprint.options:
            print(f"{'':<24}   -o {option.key}=<{option.type}> (default {option.default})")
    return 0


def _list_parts() -> int:
    from vectron.codegen.python.parts import PARTS

    for part in PARTS.values():
        print(f"{part.id:<28} {part.summary}")
        print(f"{'':<28} in: {', '.join(part.subscribes)}  out: {', '.join(part.publishes)}")
    return 0


async def _build(args: argparse.Namespace) -> int:
    from vectron.service import Factory

    options = {}
    for item in args.option:
        key, sep, value = item.partition("=")
        if not sep:
            print(f"bad --option {item!r}, expected KEY=VALUE", file=sys.stderr)
            return 2
        options[key] = value
    try:
        request = BuildRequest(blueprint_id=args.blueprint, brief=args.brief, options=options)
        factory = Factory()
        job = factory.submit(request)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    cursor = -1
    while not (job.events.closed and cursor >= len(job.events) - 1):
        for event in await job.events.wait(cursor, timeout=1.0):
            cursor = event.seq
            _print_event(job.record.tasks, event)
    assert job.runner is not None
    await job.runner

    record = job.record
    if record.status is not JobStatus.SUCCEEDED or record.bundle is None:
        print(_paint(f"build failed: {record.error}", COLORS["failed"]), file=sys.stderr)
        return 1
    data = job.workspace.bundle_path(record.bundle.filename).read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(args.out)
    project = args.out / record.bundle.filename.removesuffix(".zip")
    print(_paint(f"\n{record.title}: {record.bundle.file_count} files -> {project}", "1"))
    print(f"next: cd {project} && python -m pytest")
    return 0


def _print_event(tasks: list, event: JobEvent) -> None:  # type: ignore[type-arg]
    agent = next((t.agent for t in tasks if t.id == event.task_id), "Factory")
    kind = event.type.split(".")[-1] if event.type.startswith("task.") else event.type.split(".")[0]
    if event.type == "task.queued":
        return
    code = COLORS.get(kind) or COLORS.get(event.type.split(".")[-1])
    stamp = event.ts.strftime("%H:%M:%S.%f")[:-3]
    print(f"{stamp}  {_paint(f'{agent:<13}', code)} {event.message}")


if __name__ == "__main__":
    raise SystemExit(main())
