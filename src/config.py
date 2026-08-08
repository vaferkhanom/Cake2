from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_PATH: str = "promise_bot.db"
    DATABASE_URL: str | None = None  # Postgres URL (Railway) — overrides DB_PATH when set

    # Mini App API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    INIT_DATA_MAX_AGE_SECONDS: int = 86400  # reject initData older than 24h

    # Main menu options config (extensible)
    MENU_OPTIONS: dict = {
        "CREATE_PROMISE": "🤝 ثبت یه قول جدید",
        "LIST_PROMISES": "📋 قول‌های من",
        "PROFILE": "👤 پروفایل من"
    }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
