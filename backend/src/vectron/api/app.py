"""FastAPI application factory.

Run with ``vectron serve`` or ``uvicorn --factory vectron.api.app:create_app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
    if ui.is_dir():
        app.mount("/", StaticFiles(directory=ui, html=True), name="ui")
    return app
