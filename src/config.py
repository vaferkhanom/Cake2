from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_PATH: str = "promise_bot.db"
    
    # Main menu options config (extensible)
    MENU_OPTIONS: dict = {
        "CREATE_PROMISE": "🤝 ثبت یه قول جدید",
        "LIST_PROMISES": "📋 قول‌های من",
        "PROFILE": "👤 پروفایل من"
    }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()