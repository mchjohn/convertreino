from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from convertreino.api.routes.chat import router as chat_router
from convertreino.api.routes.health import router as health_router
from convertreino.api.routes.strava_auth import router as strava_auth_router
from convertreino.api.routes.strava_sync import router as strava_sync_router
from convertreino.api.routes.strava_webhooks import router as strava_webhooks_router
from convertreino.infrastructure.config import get_phoenix_settings
from convertreino.infrastructure.phoenix_tracing import setup_phoenix_tracing
from convertreino.mcp.server import create_mcp_app

_mcp_app = create_mcp_app()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_phoenix_tracing(get_phoenix_settings())
    async with _mcp_app.lifespan(app):
        yield


def create_app() -> FastAPI:
    app = FastAPI(title="ConverTreino", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(strava_auth_router)
    app.include_router(strava_sync_router)
    app.include_router(strava_webhooks_router)
    app.mount("/mcp", _mcp_app)
    return app


app = create_app()
