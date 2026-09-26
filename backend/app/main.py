"""FastAPI application factory (M1)."""
from fastapi import FastAPI

from chormanager import __version__ as desktop_version

from .routers import (
    availability,
    backup,
    besetzung,
    config,
    events,
    export,
    formations,
    projects,
    repertoire,
    selbstdarstellung,
    singers,
)


def create_app() -> FastAPI:
    """Build the ChorManager API application.

    Returns:
        Configured FastAPI instance (routers + health).
    """
    app = FastAPI(title="ChorManager API", version="0.1.0")
    app.include_router(singers.router)
    app.include_router(events.router)
    app.include_router(projects.router)
    app.include_router(availability.router)
    app.include_router(besetzung.router)
    app.include_router(repertoire.router)
    app.include_router(selbstdarstellung.router)
    app.include_router(formations.router)
    app.include_router(export.router)
    app.include_router(config.router)
    app.include_router(backup.router)

    @app.get("/api/health")
    def health() -> dict:
        """Liveness probe (no database access)."""
        return {"status": "ok"}

    @app.get("/api/version")
    def version() -> dict:
        """App version (Update-Check-Ersatz: kept in sync with the
        desktop ``__version__`` until the Docker release pins tags)."""
        return {"version": desktop_version}

    return app


app = create_app()
