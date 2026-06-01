from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bank_service_url: str = "http://localhost:8001"
    database_url: str = "postgresql://test:test@localhost:5432/test_db"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
