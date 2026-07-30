from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://leaddesk:leaddesk@localhost:5432/leaddesk"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    followup_job_hour: int = 8
    followup_job_minute: int = 0
    followup_days_ahead: int = 1  # notifica leads com next_action_date <= hoje + N dias


settings = Settings()
