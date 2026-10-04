import asyncio

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.health import DependencyCheck, HealthService
from app.llm import OllamaProvider, create_llm_provider
from app.main import create_app


def test_blank_password_rejected(settings):
    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "postgres_password": ""}, _env_file=None)


@pytest.mark.parametrize("url", ["https://ollama.com", "https://example.com", "http://ollama/path"])
def test_external_llm_rejected(settings, url):
    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "ollama_base_url": url}, _env_file=None)


def test_unsupported_provider_rejected(settings):
    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "llm_provider": "external"}, _env_file=None)


def test_liveness_does_not_require_dependencies(settings):
    async def run():
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/health/live")
                assert response.status_code == 200
                assert response.json() == {"status": "ok", "service": "backend"}

    asyncio.run(run())


@pytest.mark.parametrize("model,available", [("", True), ("missing", False), ("fixture", True)])
def test_ollama_probe_configuration(settings, model, available):
    async def run():
        def handler(request):
            assert request.method == "GET"
            assert request.url.path == "/api/tags"
            return httpx.Response(200, json={"models": [{"name": "fixture:latest"}]})

        config = settings.model_copy(update={"ollama_generation_model": model})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = create_llm_provider(config, client)
            assert isinstance(provider, OllamaProvider)
            report = await provider.probe()
            assert report.reachable
            assert report.configured_models_available is available
            assert report.generation_model_configured is bool(model)

    asyncio.run(run())


def test_readiness_failure_is_503_and_redacts_details(settings, monkeypatch):
    async def okay():
        return DependencyCheck(status="ok", detail="Synthetic successful probe")

    async def fail():
        raise RuntimeError(settings.postgres_password.get_secret_value())

    async def run():
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            monkeypatch.setattr(app.state.health, "postgres", fail)
            monkeypatch.setattr(app.state.health, "qdrant", okay)
            monkeypatch.setattr(app.state.health, "ollama", okay)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/health/ready")
                assert response.status_code == 503
                assert response.json()["status"] == "degraded"
                assert response.json()["checks"]["postgres"]["status"] == "error"
                assert settings.postgres_password.get_secret_value() not in response.text
                assert response.headers["cache-control"] == "no-store"

    asyncio.run(run())


def test_probe_timeout_is_bounded(settings):
    async def run():
        async def never_ready():
            await asyncio.sleep(30)

        async with httpx.AsyncClient() as client:
            service = HealthService(
                settings.model_copy(update={"health_timeout_seconds": 0.1}),
                client,
                create_llm_provider(settings, client),
            )
            result = await asyncio.wait_for(service._safe("test", never_ready), timeout=1)
            assert result.status == "error"

    asyncio.run(run())


def test_malformed_upstream_is_not_healthy(settings):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"unexpected": True}))
        ) as client:
            service = HealthService(settings, client, create_llm_provider(settings, client))
            assert (await service._safe("qdrant", service.qdrant)).status == "error"
            assert (await service._safe("ollama", service.ollama)).status == "error"

    asyncio.run(run())
