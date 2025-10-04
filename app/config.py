import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Configuration class for the Telegram bot."""
    
    # Bot token from BotFather
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # Webhook configuration
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "127.0.0.1")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8080"))
    WEBHOOK_DOMAIN: str = os.getenv("WEBHOOK_DOMAIN", "your-ngrok-domain.ngrok.io")
    WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET")
    
    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_bot_game",
    )
    DATABASE_SYNC_URL: str = os.getenv("DATABASE_SYNC_URL", "")

    # Cache configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        if not cls.WEBHOOK_DOMAIN or cls.WEBHOOK_DOMAIN == "your-ngrok-domain.ngrok.io":
            raise ValueError("WEBHOOK_DOMAIN environment variable must be set to your ngrok domain")

        return True

    @classmethod
    def get_sync_database_url(cls) -> str:
        """Return a synchronous SQLAlchemy URL for migrations and tooling."""
        if cls.DATABASE_SYNC_URL:
            return cls.DATABASE_SYNC_URL

        if cls.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return cls.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

        if cls.DATABASE_URL.startswith("sqlite+aiosqlite://"):
            return cls.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///", 1)

        return cls.DATABASE_URL


if os.getenv("CONFIG_VALIDATE_ON_IMPORT", "0") == "1":
    Config.validate()
