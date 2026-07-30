from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    owner_ids: List[int] = Field(default_factory=list, alias="OWNER_IDS")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")
    owner_username: str = Field(default="", alias="OWNER_USERNAME")

    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="telegram_vip_bot", alias="MONGO_DB")

    pakasir_slug: str = Field(alias="PAKASIR_SLUG")
    pakasir_api_key: str = Field(alias="PAKASIR_API_KEY")
    pakasir_base_url: str = Field(default="https://pakasir.zone.id", alias="PAKASIR_BASE_URL")
    payment_check_interval_seconds: int = Field(default=10, alias="PAYMENT_CHECK_INTERVAL_SECONDS")
    payment_timeout_minutes: int = Field(default=30, alias="PAYMENT_TIMEOUT_MINUTES")

    target_chat_id: int | None = Field(default=None, alias="TARGET_CHAT_ID")
    vip_channel_id: int | None = Field(default=None, alias="VIP_CHANNEL_ID")
    purchase_log_chat_id: int | None = Field(default=None, alias="PURCHASE_LOG_CHAT_ID")

    vip_price_monthly: int = Field(default=50_000, alias="VIP_PRICE_MONTHLY")
    vip_price_permanent: int = Field(default=150_000, alias="VIP_PRICE_PERMANENT")
    preview_image: str = Field(default="", alias="PREVIEW_IMAGE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("owner_ids", "admin_ids", mode="before")
    @classmethod
    def parse_ids(cls, value):
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        return [int(item.strip()) for item in str(value).split(",") if item.strip()]

    @property
    def privileged_ids(self) -> set[int]:
        return set(self.owner_ids) | set(self.admin_ids)


@lru_cache
def get_settings() -> Settings:
    return Settings()
