from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"
    cors_origins: list[str] = ["http://localhost:3000"]

    api_football_key: SecretStr = SecretStr("")
    naver_client_id: SecretStr = SecretStr("")
    naver_client_secret: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")


settings = Settings()
