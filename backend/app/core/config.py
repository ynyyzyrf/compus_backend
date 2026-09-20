from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"

    database_url: str
    test_database_url: str | None = None

    jwt_secret: str
    jwt_expire_minutes: int = 60 * 24 * 7

    wechat_appid: str = ""
    wechat_secret: str = ""
    # True only in local dev: bypass jscode2session and enable dev impersonation.
    wechat_mock_login: bool = False

    cors_origins: str = ""

    storage_driver: str = "local"
    storage_local_dir: str = "./storage_data"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = ""

    @property
    def is_dev(self) -> bool:
        return self.app_env != "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
