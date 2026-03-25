"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "signalpulse-financial-data-pipeline"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/signalpulse"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    stage0_base_url: str = "https://api.signalpulse.org"
    stage0_api_key: str = ""
    stage0_timeout_seconds: int = 30
    stage0_mock_mode: bool = False

    binance_base_url: str = "https://fapi.binance.com"
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_rate_limit_per_minute: int = 1200

    bybit_base_url: str = "https://api.bybit.com"
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_rate_limit_per_minute: int = 100

    ingestion_interval_seconds: int = 300
    ingestion_retry_max_attempts: int = 3
    ingestion_retry_backoff_seconds: int = 5
    ingestion_freshness_threshold_seconds: int = 600

    supported_symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT"

    feature_rolling_window_small: int = 10
    feature_rolling_window_medium: int = 50
    feature_rolling_window_large: int = 200
    feature_zscore_threshold: float = 2.0
    feature_min_data_points: int = 5
    feature_max_age_seconds: int = 3600

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_cors_origins: str = "http://localhost:3000,http://localhost:8080"

    secret_key: str = "change-me-in-production"
    internal_api_key: str = "change-me-in-production"

    alert_webhook_url: str = ""
    alert_retry_max_attempts: int = 3
    alert_retry_backoff_seconds: int = 10

    idempotency_key_ttl_seconds: int = 86400

    structured_logging: bool = True
    request_tracing: bool = True
    health_check_grace_period: int = 30

    @property
    def is_stage0_mock_mode(self) -> bool:
        return self.stage0_mock_mode or not self.stage0_api_key

    @property
    def supported_symbols_list(self) -> list[str]:
        return [s.strip().upper() for s in self.supported_symbols.split(",") if s.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            placeholder = "change-me-in-production"
            if self.secret_key == placeholder:
                raise ValueError("secret_key must be changed from the default value in production")
            if self.internal_api_key == placeholder:
                raise ValueError(
                    "internal_api_key must be changed from the default value in production"
                )
            if self.secret_key == self.internal_api_key:
                raise ValueError("secret_key and internal_api_key must be distinct values")
        return self

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


@lru_cache
def get_settings() -> Settings:
    return Settings()
