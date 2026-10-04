import asyncio
import os

import httpx
import pytest

from app.main import create_app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Set RUN_INTEGRATION=1"),
]


def test_real_local_dependencies():
    # Run inside the backend container using actual Compose configuration.
    async def run():
        app = create_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                assert (await client.get("/health/live")).status_code == 200
                response = await client.get("/health/ready")
                assert response.status_code == 200, response.text
                report = response.json()
                assert report["status"] == "ready"
                assert set(report["checks"]) == {"postgres", "qdrant", "ollama"}
                assert all(check["status"] == "ok" for check in report["checks"].values())
                assert report["checks"]["ollama"]["provider"]["provider"] == "ollama"

    asyncio.run(run())
