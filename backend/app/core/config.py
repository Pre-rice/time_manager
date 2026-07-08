"""应用配置，从环境变量读取"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Time Manager API"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/time_manager"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/time_manager"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Encryption (for AI keys)
    ENCRYPTION_KEY: str = "change-me-in-production-must-be-32-bytes-long!"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()