"""FastAPI application factory and entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from pedago_ai import __version__
from pedago_ai.api.v1.routes import router as api_v1_router
from pedago_ai.config import get_settings

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared resources on startup and release them on shutdown."""
    app.state.settings = get_settings()
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(api_v1_router)

    if FRONTEND_DIR.is_dir():
        # Root opens the PWA. Only registered when the frontend exists so it never
        # redirects to a missing page.
        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            return RedirectResponse(url="/app/", status_code=307)

        # Mounted last so API routes (/api/v1/...) and /health take precedence.
        app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    return app


app = create_app()
