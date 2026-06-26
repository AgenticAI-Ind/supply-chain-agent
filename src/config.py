"""
Configuration management for Supply Chain & Logistics Agent.

Loads configuration from environment variables with sensible defaults
and validation for production deployment.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Supply Chain & Logistics Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/supply_chain"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    CACHE_TTL: int = 3600  # 1 hour

    # External APIs
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    FEDEX_API_KEY: Optional[str] = None
    FEDEX_API_SECRET: Optional[str] = None
    UPS_API_KEY: Optional[str] = None
    UPS_API_SECRET: Optional[str] = None
    DHL_API_KEY: Optional[str] = None

    # ML Models
    MODEL_DIR: str = "./models"
    PROPHET_MODEL_PATH: str = "./models/prophet"
    LSTM_MODEL_PATH: str = "./models/lstm"
    RISK_MODEL_PATH: str = "./models/risk_assessment"
    MODEL_VERSION: str = "1.0.0"

    # Forecasting
    DEFAULT_FORECAST_HORIZON: int = 30
    MIN_HISTORICAL_DATA_POINTS: int = 30
    MAX_FORECAST_HORIZON: int = 365

    # Route Optimization
    DEFAULT_VEHICLE_SPEED_KMH: float = 60.0
    FUEL_COST_PER_KM: float = 0.15
    VEHICLE_COST_PER_HOUR: float = 25.0
    MAX_ROUTE_OPTIMIZATION_TIME_MS: int = 30000

    # Inventory Management
    DEFAULT_SERVICE_LEVEL: float = 0.95
    DEFAULT_HOLDING_COST_PERCENTAGE: float = 0.25
    DEFAULT_ORDERING_COST: float = 50.0
    SAFETY_STOCK_Z_SCORE: float = 1.645  # 95% service level

    # Supplier Risk Assessment
    RISK_ASSESSMENT_WEIGHTS: dict = {
        "delivery_reliability": 0.25,
        "quality": 0.25,
        "financial_stability": 0.20,
        "capacity": 0.15,
        "geopolitical": 0.10,
        "pricing": 0.05,
    }

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # Monitoring
    METRICS_ENABLED: bool = True
    SENTRY_DSN: Optional[str] = None

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


settings = Settings()
