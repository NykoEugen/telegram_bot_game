import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Iterable, Optional

from sqlalchemy import create_engine, select, delete, UniqueConstraint, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import text

from .cache import cache_delete, cache_get_json, cache_set_json
from .config import Config
from models.character import (
    ATTRIBUTE_KEYS,
    attribute_points_for_level,
    get_talent_definition,
    talent_points_for_level,
    xp_to_next_level,
)

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


class QuestRequirement(Base):
    """Stores quest prerequisite payloads as JSON."""

    __tablename__ = "quest_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    quest_id: Mapped[int] = mapped_column(ForeignKey("quests.id"), unique=True, index=True)
    payload: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<QuestRequirement(quest_id={self.quest_id})>"


class BountyTemplate(Base):
    """Static template definition for procedurally generated bounties."""

    __tablename__ = "bounty_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)  # e.g. hunt, rescue, escort
    duration_minutes: Mapped[int] = mapped_column(default=6)
    data: Mapped[str] = mapped_column(nullable=False)  # JSON payload describing template details
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<BountyTemplate(code={self.code}, category={self.category})>"


class ActiveBounty(Base):
    """Generated bounty instance available to players for a limited time."""

    __tablename__ = "active_bounties"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("bounty_templates.id"), nullable=False, index=True)
    seed: Mapped[str] = mapped_column(nullable=False)  # used to reconstruct procedural output
    payload: Mapped[str] = mapped_column(nullable=False)  # cached generated content JSON
    available_from: Mapped[str] = mapped_column(nullable=False)
    expires_at: Mapped[str] = mapped_column(nullable=False)
    tier: Mapped[str] = mapped_column(nullable=False, default="standard")

    def __repr__(self):
        return f"<ActiveBounty(id={self.id}, template_id={self.template_id}, tier={self.tier})>"


class HeroBountyProgress(Base):
    """Tracks a hero's interaction with generated bounties."""

    __tablename__ = "hero_bounty_progress"
    __table_args__ = (
        UniqueConstraint('hero_id', 'active_bounty_id', name='uq_hero_bounty'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    active_bounty_id: Mapped[int] = mapped_column(ForeignKey("active_bounties.id"), index=True)
    status: Mapped[str] = mapped_column(nullable=False, default="offered")  # offered, accepted, completed, failed
    progress_data: Mapped[str] = mapped_column(nullable=False, default='{}')
    started_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"<HeroBountyProgress(hero_id={self.hero_id}, bounty_id={self.active_bounty_id}, status={self.status})>"


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
    # For SQLite, construct both sync and async URLs explicitly
    sync_engine = create_engine(Config.get_sync_database_url(), echo=False)

    if Config.DATABASE_URL.startswith("sqlite+aiosqlite"):
        async_database_url = Config.DATABASE_URL
    else:
        async_database_url = Config.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    async_engine = create_async_engine(async_database_url, echo=False)
else:
    # For PostgreSQL/MySQL, provide both sync and async engines
    sync_engine = create_engine(Config.get_sync_database_url(), echo=False)
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


async def get_quest_by_title(session: AsyncSession, title: str) -> Optional[Quest]:
    """Get quest by title."""
    result = await session.execute(
        select(Quest).where(Quest.title == title)
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


async def get_completed_quest_ids(session: AsyncSession, user_id: int) -> set[int]:
    """Return IDs of quests the user has completed."""

    result = await session.execute(
        select(QuestProgress.quest_id).where(
            QuestProgress.user_id == user_id,
            QuestProgress.status == 'completed'
        )
    )
    return set(result.scalars().all())


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


async def upsert_quest_requirements(
    session: AsyncSession,
    quest_id: int,
    requirements: Optional[dict],
    chain: Optional[dict] = None
) -> Optional[QuestRequirement]:
    """Store quest requirement and chain metadata as JSON payload.

    Passing no data removes existing metadata.
    """

    from datetime import datetime

    result = await session.execute(
        select(QuestRequirement).where(QuestRequirement.quest_id == quest_id)
    )
    row = result.scalar_one_or_none()

    payload: dict = {}
    if requirements:
        payload['requires'] = requirements
    if chain:
        payload['chain'] = chain

    cache_key = f"quest:requirements:{quest_id}"

    if not payload:
        if row:
            await session.delete(row)
            await session.commit()
        await cache_delete(cache_key)
        return None

    payload_json = json.dumps(payload, ensure_ascii=False)
    now = datetime.utcnow().isoformat()

    if row:
        row.payload = payload_json
        row.updated_at = now
        session.add(row)
    else:
        row = QuestRequirement(
            quest_id=quest_id,
            payload=payload_json,
            created_at=now,
            updated_at=now,
        )
        session.add(row)

    await session.commit()
    await session.refresh(row)
    await cache_delete(cache_key)
    return row


async def get_quest_requirements(session: AsyncSession, quest_id: int) -> dict:
    """Return decoded quest requirements for the given quest id."""

    cache_key = f"quest:requirements:{quest_id}"
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return cached

    result = await session.execute(
        select(QuestRequirement).where(QuestRequirement.quest_id == quest_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        await cache_set_json(cache_key, {}, ttl_seconds=600)
        return {}

    try:
        payload = json.loads(row.payload)
    except json.JSONDecodeError:
        logger.warning("Invalid quest requirement JSON for quest %s", quest_id)
        await cache_set_json(cache_key, {}, ttl_seconds=120)
        return {}

    if not isinstance(payload, dict):
        await cache_set_json(cache_key, {}, ttl_seconds=120)
        return {}

    if 'requires' in payload or 'chain' in payload:
        requires = payload.get('requires', {})
    else:
        requires = payload

    if isinstance(requires, dict):
        await cache_set_json(cache_key, requires, ttl_seconds=600)
        return requires

    await cache_set_json(cache_key, {}, ttl_seconds=120)
    return {}


async def get_quest_requirements_map(
    session: AsyncSession,
    quest_ids: Iterable[int]
) -> Dict[int, dict]:
    """Return requirements payload for multiple quests in a single query."""

    quest_ids = list({int(qid) for qid in quest_ids if qid is not None})
    if not quest_ids:
        return {}

    mapping: Dict[int, dict] = {}
    missing_ids: list[int] = []

    for quest_id in quest_ids:
        cached = await cache_get_json(f"quest:requirements:{quest_id}")
        if isinstance(cached, dict):
            mapping[quest_id] = cached
        elif cached is None:
            missing_ids.append(quest_id)

    if missing_ids:
        result = await session.execute(
            select(QuestRequirement).where(QuestRequirement.quest_id.in_(missing_ids))
        )

        found_ids: set[int] = set()
        for row in result.scalars().all():
            try:
                payload = json.loads(row.payload)
            except json.JSONDecodeError:
                logger.warning("Invalid quest requirement JSON for quest %s", row.quest_id)
                await cache_set_json(f"quest:requirements:{row.quest_id}", {}, ttl_seconds=120)
                continue

            if not isinstance(payload, dict):
                await cache_set_json(f"quest:requirements:{row.quest_id}", {}, ttl_seconds=120)
                continue

            if 'requires' in payload or 'chain' in payload:
                requires = payload.get('requires', {})
            else:
                requires = payload

            if isinstance(requires, dict):
                mapping[row.quest_id] = requires
                await cache_set_json(f"quest:requirements:{row.quest_id}", requires, ttl_seconds=600)
            else:
                await cache_set_json(f"quest:requirements:{row.quest_id}", {}, ttl_seconds=120)

            found_ids.add(row.quest_id)

        for quest_id in missing_ids:
            if quest_id not in found_ids:
                await cache_set_json(f"quest:requirements:{quest_id}", {}, ttl_seconds=120)

    return mapping


async def get_quest_chain_info(session: AsyncSession, quest_id: int) -> dict:
    """Return quest chain metadata for a quest."""

    result = await session.execute(
        select(QuestRequirement).where(QuestRequirement.quest_id == quest_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {}

    try:
        payload = json.loads(row.payload)
    except json.JSONDecodeError:
        logger.warning("Invalid quest requirement JSON for quest %s", quest_id)
        return {}

    if isinstance(payload, dict):
        if 'chain' in payload and isinstance(payload['chain'], dict):
            return payload['chain']
        # Backwards compatibility: no chain info
    return {}


# Bounty helpers
async def create_bounty_template(
    session: AsyncSession,
    code: str,
    title: str,
    description: str,
    category: str,
    duration_minutes: int,
    data: dict,
    is_active: bool = True
) -> BountyTemplate:
    """Insert a new bounty template."""
    from datetime import datetime

    template = BountyTemplate(
        code=code,
        title=title,
        description=description,
        category=category,
        duration_minutes=duration_minutes,
        data=json.dumps(data, ensure_ascii=False),
        is_active=is_active,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat()
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def get_active_bounty_templates(session: AsyncSession, category: Optional[str] = None) -> list[BountyTemplate]:
    """Fetch active bounty templates, optionally filtered by category."""

    stmt = select(BountyTemplate).where(BountyTemplate.is_active == True)
    if category:
        stmt = stmt.where(BountyTemplate.category == category)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_active_bounty(
    session: AsyncSession,
    template_id: int,
    seed: str,
    payload: dict,
    available_from: str,
    expires_at: str,
    tier: str = "standard"
) -> ActiveBounty:
    """Create a generated bounty entry."""

    bounty = ActiveBounty(
        template_id=template_id,
        seed=seed,
        payload=json.dumps(payload, ensure_ascii=False),
        available_from=available_from,
        expires_at=expires_at,
        tier=tier
    )

    session.add(bounty)
    await session.commit()
    await session.refresh(bounty)
    return bounty


async def get_current_active_bounties(
    session: AsyncSession,
    now_iso: Optional[str] = None
) -> list[ActiveBounty]:
    """Return bounties that are currently available."""

    from datetime import datetime

    now = datetime.fromisoformat(now_iso) if now_iso else datetime.utcnow()

    result = await session.execute(
        select(ActiveBounty).where(
            ActiveBounty.available_from <= now.isoformat(),
            ActiveBounty.expires_at > now.isoformat()
        )
    )
    return list(result.scalars().all())


async def claim_bounty_for_hero(
    session: AsyncSession,
    hero_id: int,
    bounty_id: int
) -> HeroBountyProgress:
    """Mark bounty as accepted by the hero or return existing record."""

    result = await session.execute(
        select(HeroBountyProgress).where(
            HeroBountyProgress.hero_id == hero_id,
            HeroBountyProgress.active_bounty_id == bounty_id
        )
    )
    progress = result.scalar_one_or_none()
    if progress:
        return progress

    from datetime import datetime

    progress = HeroBountyProgress(
        hero_id=hero_id,
        active_bounty_id=bounty_id,
        status='accepted',
        progress_data='{}',
        started_at=datetime.utcnow().isoformat()
    )
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    return progress


async def complete_bounty_for_hero(
    session: AsyncSession,
    hero_id: int,
    bounty_id: int,
    success: bool = True,
    progress_data: Optional[dict] = None
) -> Optional[HeroBountyProgress]:
    """Update hero bounty progress as completed or failed."""

    result = await session.execute(
        select(HeroBountyProgress).where(
            HeroBountyProgress.hero_id == hero_id,
            HeroBountyProgress.active_bounty_id == bounty_id
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        return None

    from datetime import datetime

    progress.status = 'completed' if success else 'failed'
    progress.completed_at = datetime.utcnow().isoformat()
    if progress_data:
        progress.progress_data = json.dumps(progress_data, ensure_ascii=False)

    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    return progress


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


async def delete_graph_quest_structure(session: AsyncSession, quest_id: int) -> None:
    """Delete all graph quest nodes, connections, and progress for a quest."""
    node_ids_subquery = select(GraphQuestNode.id).where(GraphQuestNode.quest_id == quest_id)

    # Remove connections referencing the quest nodes
    await session.execute(
        delete(GraphQuestConnection).where(
            GraphQuestConnection.from_node_id.in_(node_ids_subquery)
        )
    )
    await session.execute(
        delete(GraphQuestConnection).where(
            GraphQuestConnection.to_node_id.in_(node_ids_subquery)
        )
    )

    # Remove quest progress tied to these nodes
    await session.execute(
        delete(GraphQuestProgress).where(GraphQuestProgress.quest_id == quest_id)
    )

    # Finally remove the quest nodes themselves
    await session.execute(
        delete(GraphQuestNode).where(GraphQuestNode.quest_id == quest_id)
    )

    await session.commit()


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


async def get_graph_quest_progresses_for_user(
    session: AsyncSession,
    user_id: int,
    statuses: Optional[list[str]] = None
) -> list[GraphQuestProgress]:
    """Get all graph quest progresses for a user with optional status filter."""
    query = select(GraphQuestProgress).where(GraphQuestProgress.user_id == user_id)
    if statuses:
        query = query.where(GraphQuestProgress.status.in_(statuses))

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_completed_graph_quest_ids(session: AsyncSession, user_id: int) -> set[int]:
    """Return IDs of graph quests the user has completed."""

    result = await session.execute(
        select(GraphQuestProgress.quest_id).where(
            GraphQuestProgress.user_id == user_id,
            GraphQuestProgress.status == 'completed'
        )
    )
    return set(result.scalars().all())


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

    # Progression resources
    attribute_points: Mapped[int] = mapped_column(default=0)
    talent_points: Mapped[int] = mapped_column(default=0)
    talents: Mapped[str] = mapped_column(default='[]')

    # Task tracking
    daily_progress: Mapped[str] = mapped_column(default='{}')
    weekly_progress: Mapped[str] = mapped_column(default='{}')
    daily_reset_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    weekly_reset_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    world_flags: Mapped[str] = mapped_column(nullable=False, default='{}')
    
    # Timestamps
    created_at: Mapped[str] = mapped_column(nullable=False)
    last_activity_at: Mapped[str] = mapped_column(nullable=False)
    
    def __repr__(self):
        return f"<Hero(id={self.id}, user_id={self.user_id}, name={self.name}, level={self.level})>"


class HeroReputation(Base):
    """Per-hero reputation standing with a specific faction."""

    __tablename__ = "hero_reputation"
    __table_args__ = (
        UniqueConstraint('hero_id', 'faction_code', name='uq_hero_faction'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    faction_code: Mapped[str] = mapped_column(nullable=False)
    score: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<HeroReputation(hero_id={self.hero_id}, faction_code={self.faction_code}, score={self.score})>"


class Achievement(Base):
    """Static achievement definitions stored in the database."""
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    icon: Mapped[str] = mapped_column(nullable=False, default='🏅')
    metric: Mapped[str] = mapped_column(nullable=False, index=True)
    target_value: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<Achievement(code={self.code}, target={self.target_value})>"


class HeroAchievement(Base):
    """Link table storing hero progress towards achievements."""
    __tablename__ = "hero_achievements"
    __table_args__ = (
        UniqueConstraint('hero_id', 'achievement_id', name='uq_hero_achievement'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"), index=True)
    progress: Mapped[int] = mapped_column(default=0)
    unlocked_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    progress_updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<HeroAchievement(hero_id={self.hero_id}, achievement_id={self.achievement_id}, progress={self.progress})>"


class Item(Base):
    """Item definition that can be stored in hero inventories."""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(nullable=True)
    effect_data: Mapped[str] = mapped_column(nullable=False)
    can_use_in_combat: Mapped[bool] = mapped_column(default=True)
    can_use_outside_combat: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<Item(code={self.code}, name={self.name})>"


class HeroInventoryItem(Base):
    """Hero inventory entry linking heroes to items and quantities."""
    __tablename__ = "hero_inventory"
    __table_args__ = (
        UniqueConstraint('hero_id', 'item_id', name='uq_hero_item'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hero_id: Mapped[int] = mapped_column(ForeignKey("heroes.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"<HeroInventoryItem(hero_id={self.hero_id}, item_id={self.item_id}, quantity={self.quantity})>"


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
        attribute_points=0,
        talent_points=0,
        talents='[]',
        daily_progress='{}',
        weekly_progress='{}',
        world_flags='{}',
        daily_reset_at=datetime.utcnow().isoformat(),
        weekly_reset_at=datetime.utcnow().isoformat(),
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


async def get_hero_by_id(session: AsyncSession, hero_id: int) -> Optional[Hero]:
    """Get hero by primary key."""
    result = await session.execute(
        select(Hero).where(Hero.id == hero_id)
    )
    return result.scalar_one_or_none()


async def get_hero_for_telegram(session: AsyncSession, telegram_user_id: int) -> Optional[Hero]:
    """Convenience helper to fetch hero using Telegram user id."""
    hero = await get_hero_by_user_id(session, telegram_user_id)
    if hero:
        return hero

    user = await get_user_by_telegram_id(session, telegram_user_id)
    if not user:
        return None

    return await get_hero_by_user_id(session, user.id)


async def _get_hero_reputation_row(
    session: AsyncSession,
    hero_id: int,
    faction_code: str
) -> Optional[HeroReputation]:
    result = await session.execute(
        select(HeroReputation).where(
            HeroReputation.hero_id == hero_id,
            HeroReputation.faction_code == faction_code,
        )
    )
    return result.scalar_one_or_none()


async def get_hero_reputation_value(
    session: AsyncSession,
    hero_id: int,
    faction_code: str
) -> int:
    """Return hero reputation score for given faction, defaulting to zero."""

    row = await _get_hero_reputation_row(session, hero_id, faction_code)
    return row.score if row else 0


async def get_hero_reputation_map(session: AsyncSession, hero_id: int) -> Dict[str, int]:
    """Return mapping of faction code to reputation score for the hero."""

    result = await session.execute(
        select(HeroReputation).where(HeroReputation.hero_id == hero_id)
    )
    return {row.faction_code: row.score for row in result.scalars().all()}


async def adjust_hero_reputation(
    session: AsyncSession,
    hero_id: int,
    faction_code: str,
    delta: int
) -> HeroReputation:
    """Increment hero reputation by delta, returning the updated row."""

    if delta == 0:
        row = await _get_hero_reputation_row(session, hero_id, faction_code)
        if row:
            return row

    from datetime import datetime

    row = await _get_hero_reputation_row(session, hero_id, faction_code)
    now = datetime.utcnow().isoformat()

    if row:
        row.score += delta
        row.updated_at = now
        session.add(row)
    else:
        row = HeroReputation(
            hero_id=hero_id,
            faction_code=faction_code,
            score=delta,
            updated_at=now,
        )
        session.add(row)

    await session.commit()
    await session.refresh(row)
    return row


def _deserialize_flags(raw: str | None) -> Dict[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


async def get_hero_world_flags(session: AsyncSession, hero_id: int) -> Dict[str, object]:
    """Return hero world flags as a dictionary."""

    hero = await get_hero_by_id(session, hero_id)
    if not hero:
        return {}
    return _deserialize_flags(hero.world_flags)


async def set_hero_world_flags(
    session: AsyncSession,
    hero_id: int,
    flags: Dict[str, object]
) -> Dict[str, object]:
    """Replace hero world flags with provided dictionary."""

    hero = await get_hero_by_id(session, hero_id)
    if not hero:
        raise ValueError(f"Hero with id {hero_id} not found")

    hero.world_flags = json.dumps(flags, ensure_ascii=False)
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return _deserialize_flags(hero.world_flags)


async def update_hero_world_flags(
    session: AsyncSession,
    hero_id: int,
    set_flags: Optional[Dict[str, object]] = None,
    clear_flags: Optional[Iterable[str]] = None
) -> Dict[str, object]:
    """Apply incremental world flag updates for the hero."""

    hero = await get_hero_by_id(session, hero_id)
    if not hero:
        raise ValueError(f"Hero with id {hero_id} not found")

    flags = _deserialize_flags(hero.world_flags)

    if set_flags:
        for key, value in set_flags.items():
            flags[str(key)] = value

    if clear_flags:
        for key in clear_flags:
            flags.pop(str(key), None)

    hero.world_flags = json.dumps(flags, ensure_ascii=False)
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return flags


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
    hero.experience += experience
    
    leveled_up = False
    
    # Check for level ups
    while True:
        xp_needed = xp_to_next_level(hero.level)
        if hero.experience < xp_needed:
            break

        hero.experience -= xp_needed
        hero.level += 1
        leveled_up = True

        hero.attribute_points += attribute_points_for_level(hero.level)
        hero.talent_points += talent_points_for_level(hero.level)

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

            # Recalculate max HP and heal to full when vitality grows
            total_vit = hero.base_vit + hero_class.vit_bonus
            max_hp = 20 + 4 * total_vit
            hero.current_hp = max_hp

    if leveled_up:
        hero.attribute_points = max(0, hero.attribute_points)
        hero.talent_points = max(0, hero.talent_points)

    return await update_hero(session, hero)


async def allocate_hero_attribute_point(session: AsyncSession, hero: Hero, attribute: str) -> Hero:
    """Spend one attribute point to increase a primary stat."""
    normalized = attribute.lower()
    if normalized not in ATTRIBUTE_KEYS:
        raise ValueError("Невідома характеристика")

    if hero.attribute_points <= 0:
        raise ValueError("Немає вільних очок характеристик")

    field_name = f"base_{normalized}"
    current_value = getattr(hero, field_name)
    setattr(hero, field_name, current_value + 1)
    hero.attribute_points -= 1

    return await update_hero(session, hero)


async def unlock_hero_talent(session: AsyncSession, hero: Hero, talent_id: str) -> Hero:
    """Unlock a talent for the hero if requirements are met."""
    if hero.talent_points <= 0:
        raise ValueError("Немає вільних очок талантів")

    definition = get_talent_definition(talent_id)
    if not definition:
        raise ValueError("Талант не знайдений")

    if hero.level < definition.required_level:
        raise ValueError("Рівень героя недостатній для цього таланту")

    try:
        current_talents = json.loads(hero.talents or '[]')
    except json.JSONDecodeError:
        current_talents = []

    if talent_id in current_talents:
        raise ValueError("Талант вже вивчений")

    current_talents.append(talent_id)
    hero.talents = json.dumps(current_talents)
    hero.talent_points -= 1

    return await update_hero(session, hero)


# Inventory-related database functions
async def get_item_by_code(session: AsyncSession, code: str) -> Optional[Item]:
    """Fetch an item definition by its unique code."""
    result = await session.execute(
        select(Item).where(Item.code == code)
    )
    return result.scalar_one_or_none()


async def list_items(session: AsyncSession) -> list[Item]:
    """Return all registered items."""
    result = await session.execute(select(Item))
    return list(result.scalars().all())


async def upsert_item(
    session: AsyncSession,
    code: str,
    name: str,
    description: str,
    effect_data: str,
    icon: Optional[str] = None,
    can_use_in_combat: bool = True,
    can_use_outside_combat: bool = True,
) -> Item:
    """Create or update an item definition."""
    from datetime import datetime

    item = await get_item_by_code(session, code)
    now = datetime.utcnow().isoformat()

    if item:
        item.name = name
        item.description = description
        item.effect_data = effect_data
        item.icon = icon
        item.can_use_in_combat = can_use_in_combat
        item.can_use_outside_combat = can_use_outside_combat
        item.updated_at = now
    else:
        item = Item(
            code=code,
            name=name,
            description=description,
            icon=icon,
            effect_data=effect_data,
            can_use_in_combat=can_use_in_combat,
            can_use_outside_combat=can_use_outside_combat,
            created_at=now,
            updated_at=now,
        )

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_hero_inventory_item(
    session: AsyncSession,
    hero_id: int,
    item_id: int
) -> Optional[HeroInventoryItem]:
    """Fetch a hero inventory entry for a specific item."""
    result = await session.execute(
        select(HeroInventoryItem).where(
            HeroInventoryItem.hero_id == hero_id,
            HeroInventoryItem.item_id == item_id
        )
    )
    return result.scalar_one_or_none()


async def list_hero_inventory(
    session: AsyncSession,
    hero_id: int
) -> list[tuple[HeroInventoryItem, Item]]:
    """Return all inventory entries for a hero along with item definitions."""
    result = await session.execute(
        select(HeroInventoryItem, Item)
        .join(Item, HeroInventoryItem.item_id == Item.id)
        .where(HeroInventoryItem.hero_id == hero_id)
        .order_by(Item.name.asc())
    )
    return list(result.all())


async def add_item_to_hero(
    session: AsyncSession,
    hero_id: int,
    item_code: str,
    quantity: int = 1
) -> Optional[HeroInventoryItem]:
    """Add an item to hero's inventory."""
    from datetime import datetime

    if quantity <= 0:
        return None

    item = await get_item_by_code(session, item_code)
    if not item:
        return None

    inventory_item = await get_hero_inventory_item(session, hero_id, item.id)
    now = datetime.utcnow().isoformat()

    if inventory_item:
        inventory_item.quantity += quantity
        inventory_item.updated_at = now
    else:
        inventory_item = HeroInventoryItem(
            hero_id=hero_id,
            item_id=item.id,
            quantity=quantity,
            created_at=now,
            updated_at=now,
        )

    session.add(inventory_item)
    await session.commit()
    await session.refresh(inventory_item)
    return inventory_item


async def consume_hero_item(
    session: AsyncSession,
    hero_id: int,
    item_code: str,
    quantity: int = 1
) -> bool:
    """Consume a quantity of an item from hero's inventory."""
    from datetime import datetime

    if quantity <= 0:
        return False

    item = await get_item_by_code(session, item_code)
    if not item:
        return False

    inventory_item = await get_hero_inventory_item(session, hero_id, item.id)
    if not inventory_item or inventory_item.quantity < quantity:
        return False

    inventory_item.quantity -= quantity
    if inventory_item.quantity == 0:
        await session.delete(inventory_item)
    else:
        inventory_item.updated_at = datetime.utcnow().isoformat()
        session.add(inventory_item)

    await session.commit()
    return True


async def ensure_hero_has_item(
    session: AsyncSession,
    hero_id: int,
    item_code: str,
    minimum_quantity: int = 1
) -> None:
    """Ensure hero has at least the specified quantity of an item."""
    item = await get_item_by_code(session, item_code)
    if not item:
        return

    inventory_item = await get_hero_inventory_item(session, hero_id, item.id)
    if not inventory_item:
        await add_item_to_hero(session, hero_id, item_code, minimum_quantity)
        return

    shortfall = max(0, minimum_quantity - inventory_item.quantity)
    if shortfall > 0:
        await add_item_to_hero(session, hero_id, item_code, shortfall)
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


async def get_monster_classes_by_criteria(
    session: AsyncSession, 
    monster_types: Optional[list[str]] = None,
    difficulty: Optional[str] = None
) -> list[MonsterClass]:
    """Get monster classes by multiple criteria."""
    query = select(MonsterClass)
    
    conditions = []
    
    if monster_types:
        conditions.append(MonsterClass.monster_type.in_(monster_types))
    
    if difficulty:
        conditions.append(MonsterClass.difficulty == difficulty)
    
    if conditions:
        query = query.where(*conditions)
    
    result = await session.execute(query)
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
