import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx
import psycopg
from pydantic import BaseModel

from app.config import Settings
from app.llm import LLMProvider, ProviderProbe

logger = logging.getLogger(__name__)


class DependencyCheck(BaseModel):
    status: Literal["ok", "error"]
    detail: str
    provider: ProviderProbe | None = None


class Readiness(BaseModel):
    status: Literal["ready", "degraded"]
    checks: dict[str, DependencyCheck]


class HealthService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient, provider: LLMProvider):
        self.settings = settings
        self.client = client
        self.provider = provider

    async def postgres(self) -> DependencyCheck:
        # A bounded synchronous probe in a thread also works on Windows' default
        # Proactor event loop, which psycopg's async connection does not support.
        return await asyncio.to_thread(self._postgres_query)

    def _postgres_query(self) -> DependencyCheck:
        connection = psycopg.connect(
            host=self.settings.postgres_host,
            port=self.settings.postgres_port,
            dbname=self.settings.postgres_db,
            user=self.settings.postgres_user,
            password=self.settings.postgres_password.get_secret_value(),
            connect_timeout=max(2, int(self.settings.health_timeout_seconds)),
            options="-c statement_timeout=3000",
        )
        with connection:
            cursor = connection.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise ValueError("Unexpected database probe result")
        return DependencyCheck(status="ok", detail="Authenticated SELECT 1 succeeded")

    async def qdrant(self) -> DependencyCheck:
        base_url = str(self.settings.qdrant_url).rstrip("/")
        response = await self.client.get(f"{base_url}/readyz")
        response.raise_for_status()
        response = await self.client.get(f"{base_url}/collections")
        response.raise_for_status()
        if not isinstance(response.json()["result"]["collections"], list):
            raise ValueError("Invalid Qdrant response")
        return DependencyCheck(status="ok", detail="Readiness and collection API reachable")

    async def ollama(self) -> DependencyCheck:
        probe = await self.provider.probe()
        if not probe.configured_models_available:
            return DependencyCheck(
                status="error", detail="A configured Ollama model is not installed", provider=probe
            )
        return DependencyCheck(
            status="ok",
            detail="Local server reachable; model inference is not tested by this health check",
            provider=probe,
        )

    async def _safe(
        self, name: str, probe: Callable[[], Awaitable[DependencyCheck]]
    ) -> DependencyCheck:
        try:
            return await asyncio.wait_for(probe(), timeout=self.settings.health_timeout_seconds)
        except Exception as exc:
            # Never expose connection strings, credentials or raw upstream errors.
            logger.warning("Dependency probe failed: %s (%s)", name, type(exc).__name__)
            return DependencyCheck(
                status="error", detail="Dependency unavailable or invalid response"
            )

    async def readiness(self) -> Readiness:
        names = ("postgres", "qdrant", "ollama")
        results = await asyncio.gather(
            self._safe("postgres", self.postgres),
            self._safe("qdrant", self.qdrant),
            self._safe("ollama", self.ollama),
        )
        checks = dict(zip(names, results, strict=True))
        return Readiness(
            status="ready" if all(check.status == "ok" for check in results) else "degraded",
            checks=checks,
        )
