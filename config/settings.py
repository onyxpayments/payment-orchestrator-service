from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bank_service_url: str
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()