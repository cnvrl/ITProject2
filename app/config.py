from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "TC-Explorer API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "test", "production"] = "development"

    api_prefix: str = "/api"
    host: str = "127.0.0.1"
    port: int = 8000

    data_dir: Path = Field(default=DATA_DIR)
    database_url: str = "sqlite:///./tc_records.db"

    default_region: str = "australian"
    default_data_source: Literal["simulated", "real"] = "simulated"
    default_scenario: str = "current"
    default_tracker: str = "CDD"

    cache_enabled: bool = True
    max_records_per_response: int = 10000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()