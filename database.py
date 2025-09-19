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


# Graph-based quest models
class GraphQuestNode(Base):
    """Enhanced quest node model for graph-based quests."""
    __tablename__ = "graph_quest_nodes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    quest_id: Mapped[int] = mapped_column(nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(nullable=False)  # 'start', 'choice', 'action', 'end', 'condition'
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    node_data: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON data for node-specific info
    is_final: Mapped[bool] = mapped_column(default=False)
    is_start: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<GraphQuestNode(id={self.id}, quest_id={self.quest_id}, type={self.node_type})>"


class GraphQuestConnection(Base):
    """Model for connections between quest nodes in graph structure."""
    __tablename__ = "graph_quest_connections"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    from_node_id: Mapped[int] = mapped_column(nullable=False, index=True)
    to_node_id: Mapped[int] = mapped_column(nullable=False, index=True)
    connection_type: Mapped[str] = mapped_column(nullable=False)  # 'choice', 'condition', 'default'
    choice_text: Mapped[Optional[str]] = mapped_column(nullable=True)  # Text for choice buttons
    condition_data: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON data for conditions
    order: Mapped[int] = mapped_column(default=0)  # Order of choices/connections
    
    def __repr__(self):
        return f"<GraphQuestConnection(from={self.from_node_id}, to={self.to_node_id}, type={self.connection_type})>"


class GraphQuestProgress(Base):
    """Enhanced quest progress model for graph-based quests."""
    __tablename__ = "graph_quest_progress"
    __table_args__ = (
        UniqueConstraint('user_id', 'quest_id', name='uq_graph_user_quest'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    quest_id: Mapped[int] = mapped_column(nullable=False, index=True)
    current_node_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)  # 'active', 'completed', 'declined', 'paused'
    started_at: Mapped[str] = mapped_column(nullable=False)
    completed_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    visited_nodes: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array of visited node IDs
    quest_data: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON data for quest state
    
    def __repr__(self):
        return f"<GraphQuestProgress(user_id={self.user_id}, quest_id={self.quest_id}, status={self.status})>"


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


# Graph-based quest database functions
async def create_graph_quest_node(
    session: AsyncSession,
    quest_id: int,
    node_type: str,
    title: str,
    description: str,
    node_data: Optional[str] = None,
    is_final: bool = False,
    is_start: bool = False
) -> GraphQuestNode:
    """Create a new graph quest node."""
    from datetime import datetime
    
    node = GraphQuestNode(
        quest_id=quest_id,
        node_type=node_type,
        title=title,
        description=description,
        node_data=node_data,
        is_final=is_final,
        is_start=is_start,
        created_at=datetime.utcnow().isoformat()
    )
    
    session.add(node)
    await session.commit()
    await session.refresh(node)
    
    return node


async def create_graph_quest_connection(
    session: AsyncSession,
    from_node_id: int,
    to_node_id: int,
    connection_type: str,
    choice_text: Optional[str] = None,
    condition_data: Optional[str] = None,
    order: int = 0
) -> GraphQuestConnection:
    """Create a connection between two quest nodes."""
    connection = GraphQuestConnection(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        connection_type=connection_type,
        choice_text=choice_text,
        condition_data=condition_data,
        order=order
    )
    
    session.add(connection)
    await session.commit()
    await session.refresh(connection)
    
    return connection


async def get_graph_quest_node_by_id(session: AsyncSession, node_id: int) -> Optional[GraphQuestNode]:
    """Get graph quest node by ID."""
    result = await session.execute(
        select(GraphQuestNode).where(GraphQuestNode.id == node_id)
    )
    return result.scalar_one_or_none()


async def get_graph_quest_start_node(session: AsyncSession, quest_id: int) -> Optional[GraphQuestNode]:
    """Get the start node of a graph quest."""
    result = await session.execute(
        select(GraphQuestNode).where(
            GraphQuestNode.quest_id == quest_id,
            GraphQuestNode.is_start == True
        )
    )
    return result.scalar_one_or_none()


async def get_graph_quest_connections(session: AsyncSession, from_node_id: int) -> list[GraphQuestConnection]:
    """Get all connections from a specific node."""
    result = await session.execute(
        select(GraphQuestConnection).where(
            GraphQuestConnection.from_node_id == from_node_id
        ).order_by(GraphQuestConnection.order)
    )
    return list(result.scalars().all())


async def get_graph_quest_nodes(session: AsyncSession, quest_id: int) -> list[GraphQuestNode]:
    """Get all nodes for a specific quest."""
    result = await session.execute(
        select(GraphQuestNode).where(GraphQuestNode.quest_id == quest_id)
    )
    return list(result.scalars().all())


async def create_graph_quest_progress(
    session: AsyncSession,
    user_id: int,
    quest_id: int,
    current_node_id: int,
    quest_data: Optional[str] = None
) -> GraphQuestProgress:
    """Create graph quest progress for a user."""
    from datetime import datetime
    import json
    
    # Check if progress already exists
    existing_progress = await get_user_graph_quest_progress(session, user_id, quest_id)
    if existing_progress:
        # Update existing progress
        existing_progress.current_node_id = current_node_id
        existing_progress.status = 'active'
        existing_progress.started_at = datetime.utcnow().isoformat()
        existing_progress.completed_at = None
        existing_progress.quest_data = quest_data
        
        session.add(existing_progress)
        await session.commit()
        await session.refresh(existing_progress)
        
        return existing_progress
    
    progress = GraphQuestProgress(
        user_id=user_id,
        quest_id=quest_id,
        current_node_id=current_node_id,
        status='active',
        started_at=datetime.utcnow().isoformat(),
        visited_nodes=json.dumps([current_node_id]),
        quest_data=quest_data
    )
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    return progress


async def get_user_graph_quest_progress(
    session: AsyncSession,
    user_id: int,
    quest_id: int
) -> Optional[GraphQuestProgress]:
    """Get user's graph quest progress."""
    result = await session.execute(
        select(GraphQuestProgress).where(
            GraphQuestProgress.user_id == user_id,
            GraphQuestProgress.quest_id == quest_id
        )
    )
    return result.scalar_one_or_none()


async def update_graph_quest_progress(
    session: AsyncSession,
    progress: GraphQuestProgress,
    current_node_id: Optional[int] = None,
    status: Optional[str] = None,
    quest_data: Optional[str] = None
) -> GraphQuestProgress:
    """Update graph quest progress."""
    import json
    
    if current_node_id is not None:
        progress.current_node_id = current_node_id
        
        # Update visited nodes
        visited_nodes = json.loads(progress.visited_nodes or "[]")
        if current_node_id not in visited_nodes:
            visited_nodes.append(current_node_id)
        progress.visited_nodes = json.dumps(visited_nodes)
    
    if status is not None:
        progress.status = status
        if status in ['completed', 'declined']:
            from datetime import datetime
            progress.completed_at = datetime.utcnow().isoformat()
    
    if quest_data is not None:
        progress.quest_data = quest_data
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    return progress


async def get_graph_quest_by_id(session: AsyncSession, quest_id: int) -> Optional[Quest]:
    """Get quest by ID (works for both regular and graph quests)."""
    result = await session.execute(
        select(Quest).where(Quest.id == quest_id)
    )
    return result.scalar_one_or_none()


# Monster system models
class MonsterClass(Base):
    """Monster class model for storing monster class information."""
    __tablename__ = "monster_classes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str] = mapped_column(nullable=False)
    
    # Base stats for this monster class
    base_str: Mapped[int] = mapped_column(default=5)
    base_agi: Mapped[int] = mapped_column(default=5)
    base_int: Mapped[int] = mapped_column(default=5)
    base_vit: Mapped[int] = mapped_column(default=5)
    base_luk: Mapped[int] = mapped_column(default=5)
    
    # Stat growth per level (JSON string: {"str": 1, "agi": 0, "int": 0, "vit": 1, "luk": 0})
    stat_growth: Mapped[str] = mapped_column(nullable=False, default='{"str": 0, "agi": 0, "int": 0, "vit": 0, "luk": 0}')
    
    # Monster-specific properties
    monster_type: Mapped[str] = mapped_column(nullable=False)  # 'beast', 'undead', 'demon', 'elemental', 'humanoid'
    difficulty: Mapped[str] = mapped_column(nullable=False)  # 'easy', 'normal', 'hard', 'boss'
    
    def __repr__(self):
        return f"<MonsterClass(id={self.id}, name={self.name}, type={self.monster_type})>"


class Monster(Base):
    """Monster model for storing monster instances."""
    __tablename__ = "monsters"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    monster_class_id: Mapped[int] = mapped_column(nullable=False, index=True)
    
    # Monster basic info
    name: Mapped[str] = mapped_column(nullable=False)
    level: Mapped[int] = mapped_column(default=1)
    
    # Current HP (calculated from max HP)
    current_hp: Mapped[int] = mapped_column(default=20)
    
    # Monster location and spawn info
    location: Mapped[Optional[str]] = mapped_column(nullable=True)  # Where this monster can be found
    is_active: Mapped[bool] = mapped_column(default=True)  # Whether monster is currently spawned
    
    # Timestamps
    created_at: Mapped[str] = mapped_column(nullable=False)
    last_activity_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<Monster(id={self.id}, name={self.name}, level={self.level})>"


# Hero system models
class HeroClass(Base):
    """Hero class model for storing hero class information."""
    __tablename__ = "hero_classes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str] = mapped_column(nullable=False)
    
    # Starting stats bonuses
    str_bonus: Mapped[int] = mapped_column(default=0)
    agi_bonus: Mapped[int] = mapped_column(default=0)
    int_bonus: Mapped[int] = mapped_column(default=0)
    vit_bonus: Mapped[int] = mapped_column(default=0)
    luk_bonus: Mapped[int] = mapped_column(default=0)
    
    # Stat growth per level (JSON string: {"str": 1, "agi": 0, "int": 0, "vit": 1, "luk": 0})
    stat_growth: Mapped[str] = mapped_column(nullable=False, default='{"str": 0, "agi": 0, "int": 0, "vit": 0, "luk": 0}')
    
    def __repr__(self):
        return f"<HeroClass(id={self.id}, name={self.name})>"


class Hero(Base):
    """Hero model for storing user hero information."""
    __tablename__ = "heroes"
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_hero'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    hero_class_id: Mapped[int] = mapped_column(nullable=False, index=True)
    
    # Hero basic info
    name: Mapped[str] = mapped_column(nullable=False)
    level: Mapped[int] = mapped_column(default=1)
    experience: Mapped[int] = mapped_column(default=0)
    
    # Base stats (before class bonuses and level ups)
    base_str: Mapped[int] = mapped_column(default=5)
    base_agi: Mapped[int] = mapped_column(default=5)
    base_int: Mapped[int] = mapped_column(default=5)
    base_vit: Mapped[int] = mapped_column(default=5)
    base_luk: Mapped[int] = mapped_column(default=5)
    
    # Current HP (calculated from max HP)
    current_hp: Mapped[int] = mapped_column(default=20)
    
    # Timestamps
    created_at: Mapped[str] = mapped_column(nullable=False)
    last_activity_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<Hero(id={self.id}, user_id={self.user_id}, name={self.name}, level={self.level})>"


# Town/Location system models
class Town(Base):
    """Town model for storing town/location information."""
    __tablename__ = "towns"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    town_type: Mapped[str] = mapped_column(nullable=False)  # 'village', 'city', 'outpost', etc.
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<Town(id={self.id}, name={self.name}, type={self.town_type})>"


class TownNode(Base):
    """Town node model for storing town locations/buildings."""
    __tablename__ = "town_nodes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    town_id: Mapped[int] = mapped_column(nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(nullable=False)  # 'guild', 'barracks', 'square', 'inn', etc.
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    node_data: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON data for node-specific info
    is_accessible: Mapped[bool] = mapped_column(default=True)
    required_level: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<TownNode(id={self.id}, town_id={self.town_id}, type={self.node_type}, name={self.name})>"


class TownConnection(Base):
    """Model for connections between town nodes."""
    __tablename__ = "town_connections"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    from_node_id: Mapped[int] = mapped_column(nullable=False, index=True)
    to_node_id: Mapped[int] = mapped_column(nullable=False, index=True)
    connection_type: Mapped[str] = mapped_column(nullable=False)  # 'walk', 'teleport', 'secret', etc.
    is_bidirectional: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<TownConnection(from={self.from_node_id}, to={self.to_node_id}, type={self.connection_type})>"


class UserTownProgress(Base):
    """Model for tracking user progress in towns."""
    __tablename__ = "user_town_progress"
    __table_args__ = (
        UniqueConstraint('user_id', 'town_id', name='uq_user_town'),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    town_id: Mapped[int] = mapped_column(nullable=False, index=True)
    current_node_id: Mapped[int] = mapped_column(nullable=False)
    visited_nodes: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array of visited node IDs
    town_data: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON data for town state
    first_visited_at: Mapped[str] = mapped_column(nullable=False)
    last_visited_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<UserTownProgress(user_id={self.user_id}, town_id={self.town_id}, current_node={self.current_node_id})>"


# Town-related database functions
async def create_town(
    session: AsyncSession,
    name: str,
    description: str,
    town_type: str = "village"
) -> Town:
    """Create a new town."""
    from datetime import datetime
    
    town = Town(
        name=name,
        description=description,
        town_type=town_type,
        is_active=True,
        created_at=datetime.utcnow().isoformat()
    )
    
    session.add(town)
    await session.commit()
    await session.refresh(town)
    
    return town


async def create_town_node(
    session: AsyncSession,
    town_id: int,
    node_type: str,
    name: str,
    description: str,
    node_data: Optional[str] = None,
    required_level: int = 1
) -> TownNode:
    """Create a new town node."""
    from datetime import datetime
    
    node = TownNode(
        town_id=town_id,
        node_type=node_type,
        name=name,
        description=description,
        node_data=node_data,
        is_accessible=True,
        required_level=required_level,
        created_at=datetime.utcnow().isoformat()
    )
    
    session.add(node)
    await session.commit()
    await session.refresh(node)
    
    return node


async def create_town_connection(
    session: AsyncSession,
    from_node_id: int,
    to_node_id: int,
    connection_type: str = "walk",
    is_bidirectional: bool = True
) -> TownConnection:
    """Create a connection between two town nodes."""
    from datetime import datetime
    
    connection = TownConnection(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        connection_type=connection_type,
        is_bidirectional=is_bidirectional,
        created_at=datetime.utcnow().isoformat()
    )
    
    session.add(connection)
    await session.commit()
    await session.refresh(connection)
    
    return connection


async def get_town_by_id(session: AsyncSession, town_id: int) -> Optional[Town]:
    """Get town by ID."""
    result = await session.execute(
        select(Town).where(Town.id == town_id)
    )
    return result.scalar_one_or_none()


async def get_town_node_by_id(session: AsyncSession, node_id: int) -> Optional[TownNode]:
    """Get town node by ID."""
    result = await session.execute(
        select(TownNode).where(TownNode.id == node_id)
    )
    return result.scalar_one_or_none()


async def get_town_nodes(session: AsyncSession, town_id: int) -> list[TownNode]:
    """Get all nodes for a specific town."""
    result = await session.execute(
        select(TownNode).where(TownNode.town_id == town_id)
    )
    return list(result.scalars().all())


async def get_town_connections(session: AsyncSession, from_node_id: int) -> list[TownConnection]:
    """Get all connections from a specific town node."""
    result = await session.execute(
        select(TownConnection).where(TownConnection.from_node_id == from_node_id)
    )
    return list(result.scalars().all())


async def get_town_connections_bidirectional(session: AsyncSession, node_id: int) -> list[TownConnection]:
    """Get all connections to/from a specific town node (bidirectional)."""
    result = await session.execute(
        select(TownConnection).where(
            (TownConnection.from_node_id == node_id) |
            (TownConnection.to_node_id == node_id)
        )
    )
    return list(result.scalars().all())


async def create_user_town_progress(
    session: AsyncSession,
    user_id: int,
    town_id: int,
    current_node_id: int,
    town_data: Optional[str] = None
) -> UserTownProgress:
    """Create or update user town progress."""
    from datetime import datetime
    import json
    
    # Check if progress already exists
    existing_progress = await get_user_town_progress(session, user_id, town_id)
    if existing_progress:
        # Update existing progress
        existing_progress.current_node_id = current_node_id
        existing_progress.last_visited_at = datetime.utcnow().isoformat()
        existing_progress.town_data = town_data
        
        # Update visited nodes
        visited_nodes = json.loads(existing_progress.visited_nodes or "[]")
        if current_node_id not in visited_nodes:
            visited_nodes.append(current_node_id)
        existing_progress.visited_nodes = json.dumps(visited_nodes)
        
        session.add(existing_progress)
        await session.commit()
        await session.refresh(existing_progress)
        
        return existing_progress
    
    # Create new progress
    progress = UserTownProgress(
        user_id=user_id,
        town_id=town_id,
        current_node_id=current_node_id,
        visited_nodes=json.dumps([current_node_id]),
        town_data=town_data,
        first_visited_at=datetime.utcnow().isoformat(),
        last_visited_at=datetime.utcnow().isoformat()
    )
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    return progress


async def get_user_town_progress(
    session: AsyncSession,
    user_id: int,
    town_id: int
) -> Optional[UserTownProgress]:
    """Get user's town progress."""
    result = await session.execute(
        select(UserTownProgress).where(
            UserTownProgress.user_id == user_id,
            UserTownProgress.town_id == town_id
        )
    )
    return result.scalar_one_or_none()


async def update_user_town_progress(
    session: AsyncSession,
    progress: UserTownProgress,
    current_node_id: Optional[int] = None,
    town_data: Optional[str] = None
) -> UserTownProgress:
    """Update user town progress."""
    from datetime import datetime
    import json
    
    if current_node_id is not None:
        progress.current_node_id = current_node_id
        progress.last_visited_at = datetime.utcnow().isoformat()
        
        # Update visited nodes
        visited_nodes = json.loads(progress.visited_nodes or "[]")
        if current_node_id not in visited_nodes:
            visited_nodes.append(current_node_id)
        progress.visited_nodes = json.dumps(visited_nodes)
    
    if town_data is not None:
        progress.town_data = town_data
    
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    
    return progress


# Hero-related database functions
async def create_hero_class(
    session: AsyncSession,
    name: str,
    description: str,
    str_bonus: int = 0,
    agi_bonus: int = 0,
    int_bonus: int = 0,
    vit_bonus: int = 0,
    luk_bonus: int = 0,
    stat_growth: str = '{"str": 0, "agi": 0, "int": 0, "vit": 0, "luk": 0}'
) -> HeroClass:
    """Create a new hero class."""
    hero_class = HeroClass(
        name=name,
        description=description,
        str_bonus=str_bonus,
        agi_bonus=agi_bonus,
        int_bonus=int_bonus,
        vit_bonus=vit_bonus,
        luk_bonus=luk_bonus,
        stat_growth=stat_growth
    )
    
    session.add(hero_class)
    await session.commit()
    await session.refresh(hero_class)
    
    return hero_class


async def get_hero_class_by_id(session: AsyncSession, class_id: int) -> Optional[HeroClass]:
    """Get hero class by ID."""
    result = await session.execute(
        select(HeroClass).where(HeroClass.id == class_id)
    )
    return result.scalar_one_or_none()


async def get_hero_class_by_name(session: AsyncSession, name: str) -> Optional[HeroClass]:
    """Get hero class by name."""
    result = await session.execute(
        select(HeroClass).where(HeroClass.name == name)
    )
    return result.scalar_one_or_none()


async def get_all_hero_classes(session: AsyncSession) -> list[HeroClass]:
    """Get all hero classes."""
    result = await session.execute(select(HeroClass))
    return list(result.scalars().all())


async def create_hero(
    session: AsyncSession,
    user_id: int,
    hero_class_id: int,
    name: str,
    base_str: int = 5,
    base_agi: int = 5,
    base_int: int = 5,
    base_vit: int = 5,
    base_luk: int = 5
) -> Hero:
    """Create a new hero for a user."""
    from datetime import datetime
    
    # Get hero class to calculate starting HP
    hero_class = await get_hero_class_by_id(session, hero_class_id)
    if not hero_class:
        raise ValueError(f"Hero class with ID {hero_class_id} not found")
    
    # Calculate total stats with class bonuses
    total_vit = base_vit + hero_class.vit_bonus
    
    # Calculate starting HP: HP_MAX = 20 + 4*VIT
    starting_hp = 20 + 4 * total_vit
    
    hero = Hero(
        user_id=user_id,
        hero_class_id=hero_class_id,
        name=name,
        level=1,
        experience=0,
        base_str=base_str,
        base_agi=base_agi,
        base_int=base_int,
        base_vit=base_vit,
        base_luk=base_luk,
        current_hp=starting_hp,
        created_at=datetime.utcnow().isoformat(),
        last_activity_at=datetime.utcnow().isoformat()
    )
    
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    
    return hero


async def get_hero_by_user_id(session: AsyncSession, user_id: int) -> Optional[Hero]:
    """Get hero by user ID."""
    result = await session.execute(
        select(Hero).where(Hero.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_hero(session: AsyncSession, hero: Hero) -> Hero:
    """Update hero information."""
    from datetime import datetime
    hero.last_activity_at = datetime.utcnow().isoformat()
    
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero


async def add_hero_experience(session: AsyncSession, hero: Hero, experience: int) -> Hero:
    """Add experience to hero and handle level ups."""
    import json
    
    hero.experience += experience
    
    # Check for level ups
    while True:
        xp_needed = 50 + 25 * hero.level
        if hero.experience >= xp_needed:
            # Level up
            hero.experience -= xp_needed
            hero.level += 1
            
            # Get hero class for stat growth
            hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
            if hero_class:
                stat_growth = json.loads(hero_class.stat_growth)
                
                # Apply stat growth
                hero.base_str += stat_growth.get('str', 0)
                hero.base_agi += stat_growth.get('agi', 0)
                hero.base_int += stat_growth.get('int', 0)
                hero.base_vit += stat_growth.get('vit', 0)
                hero.base_luk += stat_growth.get('luk', 0)
                
                # Recalculate max HP and heal to full
                total_vit = hero.base_vit + hero_class.vit_bonus
                max_hp = 20 + 4 * total_vit
                hero.current_hp = max_hp
        else:
            break
    
    return await update_hero(session, hero)


# Monster-related database functions
async def create_monster_class(
    session: AsyncSession,
    name: str,
    description: str,
    monster_type: str,
    difficulty: str,
    base_str: int = 5,
    base_agi: int = 5,
    base_int: int = 5,
    base_vit: int = 5,
    base_luk: int = 5,
    stat_growth: str = '{"str": 0, "agi": 0, "int": 0, "vit": 0, "luk": 0}'
) -> MonsterClass:
    """Create a new monster class."""
    monster_class = MonsterClass(
        name=name,
        description=description,
        monster_type=monster_type,
        difficulty=difficulty,
        base_str=base_str,
        base_agi=base_agi,
        base_int=base_int,
        base_vit=base_vit,
        base_luk=base_luk,
        stat_growth=stat_growth
    )
    
    session.add(monster_class)
    await session.commit()
    await session.refresh(monster_class)
    
    return monster_class


async def get_monster_class_by_id(session: AsyncSession, class_id: int) -> Optional[MonsterClass]:
    """Get monster class by ID."""
    result = await session.execute(
        select(MonsterClass).where(MonsterClass.id == class_id)
    )
    return result.scalar_one_or_none()


async def get_monster_class_by_name(session: AsyncSession, name: str) -> Optional[MonsterClass]:
    """Get monster class by name."""
    result = await session.execute(
        select(MonsterClass).where(MonsterClass.name == name)
    )
    return result.scalar_one_or_none()


async def get_all_monster_classes(session: AsyncSession) -> list[MonsterClass]:
    """Get all monster classes."""
    result = await session.execute(select(MonsterClass))
    return list(result.scalars().all())


async def get_monster_classes_by_type(session: AsyncSession, monster_type: str) -> list[MonsterClass]:
    """Get monster classes by type."""
    result = await session.execute(
        select(MonsterClass).where(MonsterClass.monster_type == monster_type)
    )
    return list(result.scalars().all())


async def get_monster_classes_by_difficulty(session: AsyncSession, difficulty: str) -> list[MonsterClass]:
    """Get monster classes by difficulty."""
    result = await session.execute(
        select(MonsterClass).where(MonsterClass.difficulty == difficulty)
    )
    return list(result.scalars().all())


async def create_monster(
    session: AsyncSession,
    monster_class_id: int,
    name: str,
    level: int = 1,
    location: Optional[str] = None
) -> Monster:
    """Create a new monster instance."""
    from datetime import datetime
    
    # Get monster class to calculate starting HP
    monster_class = await get_monster_class_by_id(session, monster_class_id)
    if not monster_class:
        raise ValueError(f"Monster class with ID {monster_class_id} not found")
    
    # Calculate starting HP based on level and VIT
    import json
    stat_growth = json.loads(monster_class.stat_growth)
    total_vit = monster_class.base_vit + (stat_growth.get('vit', 0) * (level - 1))
    starting_hp = 20 + 4 * total_vit
    
    monster = Monster(
        monster_class_id=monster_class_id,
        name=name,
        level=level,
        current_hp=starting_hp,
        location=location,
        is_active=True,
        created_at=datetime.utcnow().isoformat(),
        last_activity_at=datetime.utcnow().isoformat()
    )
    
    session.add(monster)
    await session.commit()
    await session.refresh(monster)
    
    return monster


async def get_monster_by_id(session: AsyncSession, monster_id: int) -> Optional[Monster]:
    """Get monster by ID."""
    result = await session.execute(
        select(Monster).where(Monster.id == monster_id)
    )
    return result.scalar_one_or_none()


async def get_active_monsters(session: AsyncSession) -> list[Monster]:
    """Get all active monsters."""
    result = await session.execute(
        select(Monster).where(Monster.is_active == True)
    )
    return list(result.scalars().all())


async def get_monsters_by_location(session: AsyncSession, location: str) -> list[Monster]:
    """Get monsters by location."""
    result = await session.execute(
        select(Monster).where(
            Monster.location == location,
            Monster.is_active == True
        )
    )
    return list(result.scalars().all())


async def get_monsters_by_level_range(session: AsyncSession, min_level: int, max_level: int) -> list[Monster]:
    """Get monsters within a level range."""
    result = await session.execute(
        select(Monster).where(
            Monster.level >= min_level,
            Monster.level <= max_level,
            Monster.is_active == True
        )
    )
    return list(result.scalars().all())


async def update_monster(session: AsyncSession, monster: Monster) -> Monster:
    """Update monster information."""
    from datetime import datetime
    monster.last_activity_at = datetime.utcnow().isoformat()
    
    session.add(monster)
    await session.commit()
    await session.refresh(monster)
    return monster


async def deactivate_monster(session: AsyncSession, monster: Monster) -> Monster:
    """Deactivate a monster (remove from active spawns)."""
    monster.is_active = False
    return await update_monster(session, monster)
