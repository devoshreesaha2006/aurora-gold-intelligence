from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "AURORA Commodity Intelligence"
    app_version: str = "1.0.0"
    aurora_host: str = "127.0.0.1"
    aurora_port: int = 8000
    aurora_env: str = "development"
    debug: bool = True

    # Database: SQLite default for zero-config local run, switchable to PostgreSQL
    database_url: str = "sqlite:///./aurora.db"

    # CORS origins (comma-separated or '*')
    cors_origins: str = "*"

    # Data Mode: "demo_synthetic", "staged_csv", or "live_feed_authorized"
    data_mode: str = "demo_synthetic"

    # Live Feed API credentials (optional, strictly for future authorized endpoints)
    mcx_feed_api_key: Optional[str] = None
    mcx_feed_api_secret: Optional[str] = None
    mcx_feed_base_url: Optional[str] = None

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
