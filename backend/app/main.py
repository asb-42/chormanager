"""FastAPI application factory (M1)."""
from fastapi import FastAPI

from .routers import singers


def create_app() -> FastAPI:
    """Build the ChorManager API application.

    Returns:
        Configured FastAPI instance (routers + health).
    """
    app = FastAPI(title="ChorManager API", version="0.1.0")
    app.include_router(singers.router)

    @app.get("/api/health")
    def health() -> dict:
        """Liveness probe (no database access)."""
        return {"status": "ok"}

    return app


app = create_app()
