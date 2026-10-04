from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response

from app.archive import router
from app.certificate_email import router as email_router
from app.config import Settings
from app.corpus import router as corpus_router
from app.db import migrate
from app.health import HealthService, Readiness
from app.interface_language import router as interface_router
from app.learning import router as learning_router
from app.llm import create_llm_provider
from app.media import router as media_router
from app.processing import router as processing_router
from app.recordings import router as recordings_router
from app.research import router as research_router
from app.translation import router as translation_router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or Settings()
        app.state.config = config
        if settings is None:
            migrate(config)
        async with httpx.AsyncClient(
            timeout=config.health_timeout_seconds, trust_env=False
        ) as client:
            app.state.health = HealthService(config, client, create_llm_provider(config, client))
            yield

    application = FastAPI(title="SIH26096 Foundation", version="0.1.0", lifespan=lifespan)
    application.include_router(router)
    application.include_router(processing_router)
    application.include_router(media_router)
    application.include_router(learning_router)
    application.include_router(email_router)
    application.include_router(recordings_router)
    application.include_router(research_router)
    application.include_router(corpus_router)
    application.include_router(translation_router)
    application.include_router(interface_router)

    @application.middleware("http")
    async def archive_cache_control(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/archive"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok", "service": "backend"}

    @application.get("/health/ready", response_model=Readiness)
    async def ready(request: Request, response: Response) -> Readiness:
        report = await request.app.state.health.readiness()
        response.status_code = 200 if report.status == "ready" else 503
        response.headers["Cache-Control"] = "no-store"
        return report

    return application


app = create_app()

