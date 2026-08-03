from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_PATH: str = "promise_bot.db"
    
    # Main menu options config
    MENU_OPTIONS: dict = {
        "CREATE_PROMISE": "ثبت قول",
        "LIST_PROMISES": "لیست قول ها"
    }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
