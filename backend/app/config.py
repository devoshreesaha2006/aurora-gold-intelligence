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

    # Authorized provider HTTPS bridge credentials; never expose these in API responses.
    mcx_feed_api_key: Optional[str] = None
    mcx_feed_api_secret: Optional[str] = None
    mcx_feed_base_url: Optional[str] = None
    mcx_feed_provider_name: str = "Authorized MCX Data Distributor"
    mcx_feed_quotes_path: str = "/quotes"
    mcx_feed_timeout_seconds: float = 5.0
    mcx_feed_live_max_age_seconds: int = 90
    mcx_feed_delayed_max_age_seconds: int = 1800
    mcx_feed_poll_interval_seconds: int = 5
    # Explicit operator attestation that the subscribed product's license permits
    # AURORA's intended processing and storage. Credentials alone are insufficient.
    mcx_feed_license_confirmed: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
