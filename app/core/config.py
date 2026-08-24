from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # База данных
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "task_manager_db"

    # Переменные для Docker Compose
    POSTGRES_DB: str = "task_manager_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "12345"
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    SECRET_KEY: SecretStr = SecretStr("dev-secret-key-change-it")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Telegram
    BOT_TOKEN: SecretStr = SecretStr("your-telegram-bot-token")

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Переменные в .env должны точно совпадать
        extra="ignore"  # Pydantic игнорирует все переменные из .env, которых нет в классе Settings
    )

    @property
    def DATABASE_URL(self) -> str:
        """Строка подключения к БД с asyncpg."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
