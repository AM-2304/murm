"""
FastAPI application factory.

Replaces MiroFish's synchronous Flask server.
Key improvements:
  - Full async throughout - no blocking I/O on the main thread
  - SSE endpoint for real-time simulation progress (no frontend polling)
  - Structured JSON errors with clear status codes
  - Auto-generated OpenAPI docs at /docs
  - CORS configured via settings
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from murm.api.routes import graph, projects, runs, stream
from murm.api.store import ProjectStore
from murm.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    store: ProjectStore = app.state.store
    await store.initialize()
    logger.info("MURM API ready on %s:%s", settings.api_host, settings.api_port)
    yield
    logger.info("MURM API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="MURM",
        description="Swarm intelligence prediction engine API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.store = ProjectStore(settings.data_dir / "murm.db")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
    app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(stream.router, prefix="/api/stream", tags=["stream"])

    return app
