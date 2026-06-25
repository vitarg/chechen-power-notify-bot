from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    source_api_url: str = Field(
        default="https://chechenenergo.ru/wp-json/tribe/events/v1/events",
        alias="SOURCE_API_URL",
    )
    source_calendar_url: str = Field(
        default="https://chechenenergo.ru/events/mesyacz/",
        alias="SOURCE_CALENDAR_URL",
    )
    timezone: str = Field(default="Europe/Moscow", alias="TIMEZONE")
    lookahead_days: int = Field(default=30, alias="LOOKAHEAD_DAYS")
    error_alert_threshold: int = Field(default=3, alias="ERROR_ALERT_THRESHOLD")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: object) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        return [int(item.strip()) for item in str(value).split(",") if item.strip()]

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()

