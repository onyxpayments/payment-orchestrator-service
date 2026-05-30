from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mock_bank_base_url: str = "http://localhost:8001"

    class Config:
        env_file = ".env"


settings = Settings()
