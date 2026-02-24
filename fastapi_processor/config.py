"""
FastAPI Application Configuration
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    POSTGRES_DB: str = "ai_platform"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "Vishal321"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # JWT (must match Django's config)
    JWT_SECRET_KEY: str = "a300e30e58f81cd2e06b6f27dcae6440629d190026e68e9fd3f9bfaaa572a8f796f66a3b0f146936ef2eee55c353752b09b9"
    JWT_ALGORITHM: str = "HS256"

    # OpenAI
    OPENAI_API_KEY: str = "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"
    AI_MODEL: str = "gpt-3.5-turbo"

    # File Processing
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "/app/uploads"

    # Django (for webhook / token validation)
    DJANGO_BASE_URL: str = "http://django:8000"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
