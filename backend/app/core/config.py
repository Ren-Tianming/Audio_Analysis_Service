from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数から読み込むアプリケーション設定。"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUDIO_", extra="ignore")

    app_name: str = "RyThM_Music_Analys"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://audio_user:audio_password@localhost:3306/audio_analysis?charset=utf8mb4"
    jwt_secret_key: str = Field(default="change-this-secret-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    timezone: str = "Asia/Tokyo"
    upload_dir: Path = Path("storage/uploads")
    max_upload_bytes: int = 50 * 1024 * 1024
    max_audio_duration_sec: int = 600
    analysis_points_cost: int = 5
    registration_bonus: int = 20
    daily_login_bonus: int = 10
    auto_create_tables: bool = False

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def tokyo_tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
