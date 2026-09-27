"""Command line: ``vectron serve | blueprints | parts | build``."""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
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

    start = commands.add_parser(
        "start", help="build the web UI if needed, serve everything on one port, open a browser"
    )
    start.add_argument("--port", type=int, default=8000)
    start.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    start.add_argument(
        "--engine",
        choices=["auto", "claude-code", "anthropic", "offline"],
        default="auto",
        help="AI engine; auto uses Claude Code (your subscription) when installed, else offline",
    )

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
    if args.command == "start":
        return _start(args.port, open_browser=not args.no_browser, engine=args.engine)
    if args.command == "blueprints":
        return _list_blueprints()
    if args.command == "parts":
        return _list_parts()
    return asyncio.run(_build(args))


# backend/src/vectron/cli.py -> repository root -> frontend/
FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


def _ui_is_stale(frontend: Path) -> bool:
    """True when frontend/dist is missing or older than any UI source file."""
    built = frontend / "dist" / "index.html"
    if not built.is_file():
        return True
    sources = [frontend / "index.html", frontend / "package.json", *(frontend / "src").rglob("*")]
    newest = max((f.stat().st_mtime for f in sources if f.is_file()), default=0.0)
    return newest > built.stat().st_mtime


def _ensure_ui(frontend: Path) -> bool:
    """Install and build the web UI when needed. Returns False if it cannot be built."""
    if not _ui_is_stale(frontend):
        return True
    npm = shutil.which("npm")
    if npm is None:
        print(
            "Node.js (npm) was not found, so the web UI cannot be built.\n"
            "Install the LTS version from https://nodejs.org, reopen your terminal and retry.",
            file=sys.stderr,
        )
        return False
    steps = [[npm, "install"]] if not (frontend / "node_modules").is_dir() else []
    steps.append([npm, "run", "build"])
    for step in steps:
        print(f"Building the web UI: {' '.join(step[1:])} ...")
        if subprocess.run(step, cwd=frontend).returncode != 0:
            print(f"`npm {' '.join(step[1:])}` failed; see the output above.", file=sys.stderr)
            return False
    return True


def _start(port: int, open_browser: bool, engine: str = "auto") -> int:
    """One command for everything: build the UI if needed, then serve UI + API together."""
    import uvicorn

    if not _ensure_ui(FRONTEND_DIR):
        return 1
    # A short per-task delay so the assembly line is visible in the UI.
    os.environ.setdefault("VECTRON_PACING_SECONDS", "0.4")
    # Use Claude through the local Claude Code login when it is installed.
    if engine != "auto":
        os.environ["VECTRON_LLM_PROVIDER"] = engine
    elif "VECTRON_LLM_PROVIDER" not in os.environ:
        os.environ["VECTRON_LLM_PROVIDER"] = "claude-code" if shutil.which("claude") else "offline"
    print(f"Engine: {os.environ['VECTRON_LLM_PROVIDER']}")
    url = f"http://localhost:{port}"
    print(f"\nVectron is running at {url}  (press Ctrl+C to stop)\n")
    if open_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run("vectron.api.app:create_app", factory=True, host="127.0.0.1", port=port)
    return 0


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
