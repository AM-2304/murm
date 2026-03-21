"""
Central configuration loaded from environment variables or .env file.
All components import from here - no scattered os.environ calls.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM provider - any string litellm understands, e.g. "gpt-4o", "claude-3-5-sonnet-20241022",
    # "ollama/llama3", "groq/llama3-8b-8192", "anthropic/claude-3-haiku-20240307"
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")

    # Separate smaller model for cheap per-agent inference during simulation rounds.
    # Falls back to llm_model if unset.
    agent_model: str | None = Field(default=None, alias="AGENT_MODEL")
    agent_api_key: str | None = Field(default=None, alias="AGENT_API_KEY")
    agent_base_url: str | None = Field(default=None, alias="AGENT_BASE_URL")

    # Token budget (0 = unlimited)
    token_budget: int = Field(default=0, alias="TOKEN_BUDGET")

    # Storage — all runtime data lives here, fully local
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")

    # Vector store — ChromaDB persistent path
    chroma_path: Path = Field(default=Path("data/chroma"), alias="CHROMA_PATH")

    # API server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Simulation defaults (all overridable per-run)
    default_agents: int = Field(default=50, alias="DEFAULT_AGENTS")
    default_rounds: int = Field(default=30, alias="DEFAULT_ROUNDS")
    default_seed: int = Field(default=42, alias="DEFAULT_SEED")

    # Log level
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")

    @field_validator("data_dir", "chroma_path", mode="before")
    @classmethod
    def coerce_path(cls, v: str | Path) -> Path:
        return Path(v)

    @property
    def cors_origins(self) -> list[str]:
        # Accepts: comma-separated, JSON array string, or single URL
        v = self.cors_origins_raw.strip()
        if v.startswith("["):
            import json
            return json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def agent_model_resolved(self) -> str:
        return self.agent_model or self.llm_model

    @property
    def agent_api_key_resolved(self) -> str | None:
        return self.agent_api_key or self.llm_api_key

    @property
    def agent_base_url_resolved(self) -> str | None:
        return self.agent_base_url or self.llm_base_url

    def ensure_dirs(self) -> None:
        for d in [self.data_dir, self.chroma_path,
                  self.data_dir / "projects", self.data_dir / "simulations"]:
            d.mkdir(parents=True, exist_ok=True)


# Module-level singleton. Import as: from murm.config import settings
settings = Settings()