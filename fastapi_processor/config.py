"""
FastAPI Application Configuration
Properly loads from environment variables with secure defaults
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database Configuration
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ai_platform")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")  # Must be set in env
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    # For Render: accepts DATABASE_URL directly
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT Configuration (must match Django's config)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")  # Must be set in env
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")  # Must be set in env
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-3.5-turbo")

    # File Processing
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")

    # Django Integration (for webhook / token validation)
    DJANGO_BASE_URL: str = os.getenv("DJANGO_BASE_URL", "http://localhost:8000")

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:80"
    )

    # Environment
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    def get_database_url(self) -> str:
        """Construct or return database URL based on configuration."""
        # If DATABASE_URL is provided (Render), use it directly
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # Otherwise construct from individual components
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    def get_cors_origins(self) -> list:
        """Parse CORS origins from environment variable."""
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


settings = Settings()

# Validate critical environment variables
if not settings.JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")

if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

if not settings.POSTGRES_PASSWORD and not settings.DATABASE_URL:
    raise ValueError(
        "Either POSTGRES_PASSWORD or DATABASE_URL environment variable is required"
    )
