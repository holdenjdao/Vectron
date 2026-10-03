"""FastAPI application factory.

Run with ``vectron serve`` or ``uvicorn --factory vectron.api.app:create_app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from vectron import __version__
from vectron.service import Factory

from .routes import router

# backend/src/vectron/api/app.py -> repository root -> frontend/dist
_DEFAULT_UI = Path(__file__).resolve().parents[4] / "frontend" / "dist"


def create_app(factory: Factory | None = None) -> FastAPI:
    factory = factory or Factory()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await factory.shutdown()

    app = FastAPI(
        title="Vectron",
        version=__version__,
        summary="Agent-orchestrated software factory: diagrams and modular code from blueprints.",
        lifespan=lifespan,
    )
    app.state.factory = factory
    app.include_router(router, prefix="/api")

    ui = factory.settings.static_dir or _DEFAULT_UI
    if (ui / "index.html").is_file():
        app.mount("/", StaticFiles(directory=ui, html=True), name="ui")
    else:

        @app.get("/", include_in_schema=False, response_class=HTMLResponse)
        def ui_not_built() -> str:
            return _NO_UI_PAGE

    return app


# Shown at "/" when the web UI has not been built, instead of a bare 404.
_NO_UI_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vectron API</title>
<style>
  body { background: #070b10; color: #d7e3ee; font: 15px/1.6 system-ui, sans-serif;
         max-width: 640px; margin: 10vh auto; padding: 0 16px; }
  h1 { font-size: 18px; letter-spacing: .25em; }
  pre, code { font-family: ui-monospace, Menlo, Consolas, monospace; background: #0c131b;
              border: 1px solid #1b2a38; border-radius: 4px; }
  pre { padding: 12px 14px; } code { padding: 1px 5px; }
  a { color: #38e0a0; }
</style>
</head>
<body>
<h1>VECTRON</h1>
<p>The API is running. The web interface is a separate app that has not been built yet.</p>
<p>Leave this server running, open a <strong>second terminal</strong> in the repository and run:</p>
<pre>cd frontend
npm install
npm run dev</pre>
<p>Then open <a href="http://localhost:5173">http://localhost:5173</a>.</p>
<p>Alternatively, run <code>npm run build</code> once in <code>frontend/</code>
and reload this page to have this server show the interface itself.</p>
<p>API documentation: <a href="/docs">/docs</a></p>
</body>
</html>
"""
