from pathlib import Path
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    data_dir: Path = ROOT / "database" / "data"
    sources_file: Path = ROOT / "backend" / "sources.json"
    timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    report_hour: int = Field(default=8, ge=0, le=23)
    report_minute: int = Field(default=0, ge=0, le=59)
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout: int = Field(default=35, ge=5, le=120)
    feed_timeout: int = Field(default=15, ge=1, le=60)
    max_per_section: int = Field(default=10, ge=1, le=10)
    candidate_multiplier: int = Field(default=2, ge=1, le=3)
    admin_token: str = ""
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    allowed_hosts: str = "localhost,127.0.0.1,api,testserver"
    cookie_secure: bool = False
    session_days: int = Field(default=30, ge=1, le=90)
    allow_registration: bool = True
    auth_rate_limit: int = Field(default=12, ge=1, le=100)
    push_provider: Literal["disabled", "jpush"] = "disabled"
    jpush_app_key: str = ""
    jpush_master_secret: str = ""
    push_timeout: int = Field(default=10, ge=2, le=30)

    @property
    def push_enabled(self):
        return self.push_provider == "jpush" and bool(self.jpush_app_key and self.jpush_master_secret)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_base_url and self.ai_model)

    @property
    def db_url(self) -> str:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.data_dir / 'news.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
