from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    sqlite_path: str = "./data/alpha_a5.db"
    jwt_secret_key: str = "change-this-secret"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    redis_url: str = "redis://localhost:6379/0"
    redis_max_retry_count: int = 3
    default_admin_username: str | None = "admin"
    default_admin_password: str | None = "admin123456"
    default_admin_display_name: str = "Alpha Admin"

    @property
    def sqlite_file_path(self) -> Path:
        return Path(self.sqlite_path).expanduser().resolve()

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.sqlite_file_path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
