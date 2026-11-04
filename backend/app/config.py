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
    # Run only news on an instance that should not start the other collection/AI jobs.
    news_scheduler_enabled: bool = False

    # API-Football protection (Pro plan: 7,500/day, 300/min).
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_daily_budget: int = 7000
    api_football_per_minute: int = 250

    # Current season as the API season value (2026 = 2026-27, CMP-003). Main schedule,
    # team search and the team-detail allow set use it.
    current_season: int = 2026
    # true: crest/logo URLs are sent only for rights-cleared assets (V-10). None is cleared
    # yet, so every image falls back to the placeholder. false (local default): API URLs.
    image_rights_enforced: bool = False
    # How long collected news metadata is kept and shown (V-09 decides the final value).
    news_retention_hours: int = 72
    naver_news_base_url: str = "https://naverapihub.apigw.ntruss.com"

    api_football_key: SecretStr = SecretStr("")
    naver_client_id: SecretStr = SecretStr("")
    naver_client_secret: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")
    # Discord channel webhook for new feedback. The URL contains a token: keep it secret.
    # Empty = notifications off (feedback is still stored).
    feedback_discord_webhook_url: SecretStr = SecretStr("")

    # AI weekly TOP 5 (chat 04, docs/TOP5_POLICY). The key goes straight to the SDK client;
    # GOOGLE_API_KEY is never read. Free tier: only public match data is sent.
    gemini_api_key: SecretStr = SecretStr("")
    top5_llm_model: str = "gemini-3.8-flash"
    # Each automatic attempt must end (success, failure or timeout) before the next fixed
    # slot: 00:00 -> 00:05 KST leaves 5 minutes, so the default stops at 4.
    top5_attempt_timeout_seconds: int = 240
    # Separate Discord channel for operator alerts (second failure). Empty = alerts off.
    top5_alert_discord_webhook_url: SecretStr = SecretStr("")


settings = Settings()
