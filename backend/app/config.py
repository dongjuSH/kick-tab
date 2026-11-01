from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"
    # Browser origins allowed for CORS and for the CSRF Origin check.
    cors_origins: list[str] = ["http://localhost:3000"]
    # X-Forwarded-For is trusted only when the direct peer is one of these (the local
    # Next.js rewrite proxy by default).
    trusted_proxies: list[str] = ["127.0.0.1", "::1"]

    # Only one instance may run the in-process scheduler (guide §6.5).
    scheduler_enabled: bool = False

    # API-Football protection (Pro plan: 7,500/day, 300/min).
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_daily_budget: int = 7000
    api_football_per_minute: int = 250

    api_football_key: SecretStr = SecretStr("")
    naver_client_id: SecretStr = SecretStr("")
    naver_client_secret: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")
    # Discord channel webhook for new feedback. The URL contains a token: keep it secret.
    # Empty = notifications off (feedback is still stored).
    feedback_discord_webhook_url: SecretStr = SecretStr("")


settings = Settings()
