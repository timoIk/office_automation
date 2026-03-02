from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Telegram
    telegram_bot_token: str = ""
    allowed_user_ids: str = ""  # Kommasepariert

    # Anthropic
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite:///data/office_automation.db"

    # Logging
    log_level: str = "INFO"

    @property
    def allowed_user_id_list(self) -> list[int]:
        if not self.allowed_user_ids:
            return []
        return [int(uid.strip()) for uid in self.allowed_user_ids.split(",") if uid.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
