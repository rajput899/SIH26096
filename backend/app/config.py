from typing import Literal

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True, populate_by_name=True
    )

    postgres_host: str = "postgres"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(min_length=1)
    postgres_user: str = Field(min_length=1)
    postgres_password: SecretStr
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://qdrant:6333")
    llm_provider: Literal["ollama"] = "ollama"
    ai_provider: Literal["ollama", "gemini"] = "ollama"
    gemini_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    gemini_model: str = Field(default="", max_length=100)
    bhashini_udyat_key: SecretStr = Field(
        default=SecretStr(""),
        repr=False,
        validation_alias=AliasChoices("BHASHINI_UDYAT_KEY", "Udyat_Key"),
    )
    bhashini_inference_key: SecretStr = Field(
        default=SecretStr(""),
        repr=False,
        validation_alias=AliasChoices("BHASHINI_INFERENCE_KEY", "Inference"),
    )
    bhashini_user_id: SecretStr = Field(default=SecretStr(""), repr=False)
    bhashini_pipeline_id: str = ""
    bhashini_translation_service_id: str = "bhashini/iiith/nmt-all"
    translation_timeout_seconds: float = Field(default=20, ge=1, le=45)
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = ""
    smtp_password: SecretStr = Field(default=SecretStr(""), repr=False)
    smtp_from: str = ""
    certificate_public_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://ollama:11434")
    ollama_generation_model: str = ""
    ollama_embedding_model: str = ""
    health_timeout_seconds: float = Field(default=3, ge=0.1, le=10)
    archive_root: str = "/app/archive"
    processing_timeout_seconds: int = Field(default=180, ge=10, le=600)
    research_collection: str = Field(default="verified_archive_v1", pattern=r"^[a-zA-Z0-9_-]+$")
    generation_timeout_seconds: int = Field(default=45, ge=5, le=60)

    @field_validator("postgres_password")
    @classmethod
    def require_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("POSTGRES_PASSWORD must be set; run scripts/init_env.py")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def local_ollama_only(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        # No cloud URL, URL credentials, or accidental external provider fallback.
        import ipaddress

        host = value.host or ""
        local = host in {"ollama", "localhost", "host.docker.internal"}
        try:
            address = ipaddress.ip_address(host.strip("[]"))
            local = address.is_loopback or address.is_private
        except ValueError:
            pass
        if not local or value.username or value.password or value.path not in (None, "/"):
            raise ValueError("OLLAMA_BASE_URL must point to a local Ollama server")
        if value.query or value.fragment:
            raise ValueError("OLLAMA_BASE_URL must not contain query or fragment data")
        return value
