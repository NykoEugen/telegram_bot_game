import asyncio
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import text

from config import Config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class User(Base):
    """User model for storing Telegram user information."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(unique=True, index=True)  # Telegram user ID
    username: Mapped[Optional[str]] = mapped_column(nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_bot: Mapped[bool] = mapped_column(default=False)
    language_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[str] = mapped_column(nullable=False)  # ISO format datetime string
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"


# Database setup
if Config.DATABASE_URL.startswith("sqlite"):
    # For SQLite, use synchronous engine for migrations
    sync_engine = create_engine(Config.DATABASE_URL.replace("sqlite:///", "sqlite:///"), echo=False)
    
    # Create async engine for SQLite
    async_database_url = Config.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    async_engine = create_async_engine(async_database_url, echo=False)
else:
    # For PostgreSQL/MySQL, use async engine
    async_engine = create_async_engine(Config.DATABASE_URL, echo=False)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    try:
        # Create tables using sync engine for SQLite compatibility
        if Config.DATABASE_URL.startswith("sqlite"):
            Base.metadata.create_all(bind=sync_engine)
            logger.info("Database tables created successfully")
        else:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_bot: bool = False,
    language_code: Optional[str] = None
) -> User:
    """Create a new user in the database."""
    from datetime import datetime
    
    user = User(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_bot=is_bot,
        language_code=language_code,
        created_at=datetime.utcnow().isoformat()
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_user_id: int) -> Optional[User]:
    """Get user by Telegram user ID."""
    result = await session.execute(
        select(User).where(User.user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def update_user(session: AsyncSession, user: User) -> User:
    """Update user information."""
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
