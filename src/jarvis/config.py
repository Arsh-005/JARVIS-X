from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "JARVIS-X"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    database_path: Path = Path("data/jarvis.db")
    database_url: str = ""
    redis_url: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "jarvis-memory"
    workspace_dir: Path = Path("workspace")
    upload_dir: Path = Path("data/uploads")
    log_level: str = "INFO"

    llm_provider: Literal["auto", "openai", "gemini", "local"] = "auto"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_timeout_seconds: int = Field(default=45, ge=5, le=180)
    max_agent_steps: int = Field(default=8, ge=1, le=30)
    max_tool_calls: int = Field(default=10, ge=1, le=50)
    max_context_chars: int = Field(default=14000, ge=1000, le=100000)

    enable_local_computer_tools: bool = False
    allow_web_fetch: bool = True
    require_confirmation_for_writes: bool = True
    web_fetch_allowed_hosts: str = ""
    audit_log_path: Path = Path("data/audit.jsonl")
    api_key: str = ""
    jwt_secret: str = ""
    cors_origins: str = "http://localhost:8000"
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    enable_prometheus: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def allowed_hosts(self) -> set[str]:
        return {h.strip().lower() for h in self.web_fetch_allowed_hosts.split(",") if h.strip()}

    def ensure_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
