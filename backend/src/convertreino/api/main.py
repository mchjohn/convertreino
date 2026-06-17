from fastapi import FastAPI

from convertreino.api.routes.health import router as health_router
from convertreino.api.routes.strava_auth import router as strava_auth_router
from convertreino.api.routes.strava_sync import router as strava_sync_router


def create_app() -> FastAPI:
    app = FastAPI(title="ConverTreino")
    app.include_router(health_router)
    app.include_router(strava_auth_router)
    app.include_router(strava_sync_router)
    return app


app = create_app()
