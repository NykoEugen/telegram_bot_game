import asyncio
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, select, UniqueConstraint
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


class Quest(Base):
    """Quest model for storing quest information."""
    __tablename__ = "quests"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<Quest(id={self.id}, title={self.title})>"


class QuestNode(Base):
    """Quest node model for storing quest story nodes."""
    __tablename__ = "quest_nodes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    quest_id: Mapped[int] = mapped_column(nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(nullable=False)  # 'start', 'choice', 'end'
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    next_node_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_final: Mapped[bool] = mapped_column(default=False)
    
    def __repr__(self):
        return f"<QuestNode(id={self.id}, quest_id={self.quest_id}, type={self.node_type})>"


class QuestProgress(Base):
    """Quest progress model for tracking user progress through quests."""
    __tablename__ = "quest_progress"
    __table_args__ = (
        UniqueConstraint('user_id', 'quest_id', name='uq_user_quest'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    quest_id: Mapped[int] = mapped_column(nullable=False, index=True)
    current_node_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)  # 'active', 'completed', 'declined'
    started_at: Mapped[str] = mapped_column(nullable=False)
    completed_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    def __repr__(self):
        return f"<QuestProgress(user_id={self.user_id}, quest_id={self.quest_id}, status={self.status})>"


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


# Quest-related database functions
async def create_quest(
    session: AsyncSession,
    title: str,
    description: str
) -> Quest:
    """Create a new quest."""
    from datetime import datetime
    
    quest = Quest(
        title=title,
        description=description,
        is_active=True,
        created_at=datetime.utcnow().isoformat()
    )
    
    session.add(quest)
    await session.commit()
    await session.refresh(quest)
    
    return quest


async def create_quest_node(
    session: AsyncSession,
    quest_id: int,
    node_type: str,
    title: str,
    description: str,
    next_node_id: Optional[int] = None,
    is_final: bool = False
) -> QuestNode:
    """Create a new quest node."""
    node = QuestNode(
        quest_id=quest_id,
        node_type=node_type,
        title=title,
        description=description,
        next_node_id=next_node_id,
        is_final=is_final
    )
    
    session.add(node)
    await session.commit()
    await session.refresh(node)
    
    return node


async def get_quest_by_id(session: AsyncSession, quest_id: int) -> Optional[Quest]:
    """Get quest by ID."""
    result = await session.execute(
        select(Quest).where(Quest.id == quest_id)
    )
    return result.scalar_one_or_none()


async def get_quest_node_by_id(session: AsyncSession, node_id: int) -> Optional[QuestNode]:
    """Get quest node by ID."""
    result = await session.execute(
        select(QuestNode).where(QuestNode.id == node_id)
    )
    return result.scalar_one_or_none()


async def get_quest_start_node(session: AsyncSession, quest_id: int) -> Optional[QuestNode]:
    """Get the start node of a quest."""
    result = await session.execute(
        select(QuestNode).where(
            QuestNode.quest_id == quest_id,
            QuestNode.node_type == 'start'
        )
    )
    return result.scalar_one_or_none()


async def create_quest_progress(
    session: AsyncSession,
    user_id: int,
    quest_id: int,
    current_node_id: int
) -> QuestProgress:
    """Create quest progress for a user."""
    from datetime import datetime
    
    # Check if progress already exists
    existing_progress = await get_user_quest_progress(session, user_id, quest_id)
    if existing_progress:
        # Update existing progress instead of creating new one
        existing_progress.current_node_id = current_node_id
        existing_progress.status = 'active'
        existing_progress.started_at = datetime.utcnow().isoformat()
        existing_progress.completed_at = None
        
        session.add(existing_progress)
        await session.commit()
        await session.refresh(existing_progress)
        
        return existing_progress
    
    progress = QuestProgress(
        user_id=user_id,
        quest_id=quest_id,
        current_node_id=current_node_id,
        status='active',
        started_at=datetime.utcnow().isoformat()
    )
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    return progress


async def get_user_quest_progress(
    session: AsyncSession,
    user_id: int,
    quest_id: int
) -> Optional[QuestProgress]:
    """Get user's quest progress."""
    result = await session.execute(
        select(QuestProgress).where(
            QuestProgress.user_id == user_id,
            QuestProgress.quest_id == quest_id
        )
    )
    # Handle multiple results by returning the first one (most recent)
    progress_list = result.scalars().all()
    if progress_list:
        return progress_list[0]
    return None


async def update_quest_progress(
    session: AsyncSession,
    progress: QuestProgress,
    current_node_id: Optional[int] = None,
    status: Optional[str] = None
) -> QuestProgress:
    """Update quest progress."""
    if current_node_id is not None:
        progress.current_node_id = current_node_id
    if status is not None:
        progress.status = status
        if status in ['completed', 'declined']:
            from datetime import datetime
            progress.completed_at = datetime.utcnow().isoformat()
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    return progress


async def get_active_quests(session: AsyncSession) -> list[Quest]:
    """Get all active quests."""
    result = await session.execute(
        select(Quest).where(Quest.is_active == True)
    )
    return list(result.scalars().all())
