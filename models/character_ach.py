"""Helpers for tracking hero achievements and progress."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.achievement import AchievementDefinition, achievements_by_metric, all_achievements


@dataclass
class AchievementProgress:
    """Runtime view of a hero's achievement progress."""

    definition: AchievementDefinition
    progress: int
    unlocked: bool
    target_value: int
    unlocked_at: str | None

    @property
    def completion_percent(self) -> int:
        if self.target_value <= 0:
            return 100
        return min(100, int((self.progress / self.target_value) * 100))


class AchievementTracker:
    """Utility class that keeps hero achievement progress in sync."""

    @staticmethod
    async def ensure_definitions(session: AsyncSession) -> None:
        """Sync static achievement definitions into the database."""
        from app.database import Achievement  # Local import to avoid circular dependency

        existing = await session.execute(select(Achievement))
        existing_by_code = {row.code: row for row in existing.scalars().all()}
        changed = False
        now = datetime.utcnow().isoformat()

        for definition in all_achievements():
            db_row = existing_by_code.get(definition.code)
            if not db_row:
                session.add(
                    Achievement(
                        code=definition.code,
                        name=definition.name,
                        description=definition.description,
                        icon=definition.icon,
                        metric=definition.metric,
                        target_value=definition.target_value,
                        created_at=now,
                        updated_at=now,
                    )
                )
                changed = True
                continue

            if (
                db_row.name != definition.name
                or db_row.description != definition.description
                or db_row.icon != definition.icon
                or db_row.metric != definition.metric
                or db_row.target_value != definition.target_value
            ):
                db_row.name = definition.name
                db_row.description = definition.description
                db_row.icon = definition.icon
                db_row.metric = definition.metric
                db_row.target_value = definition.target_value
                db_row.updated_at = now
                changed = True

        if changed:
            await session.commit()

    @staticmethod
    async def record_metric(
        session: AsyncSession,
        hero,
        metric: str,
        amount: int = 1,
    ) -> List[AchievementDefinition]:
        """Increment hero progress for a metric and return newly unlocked achievements."""
        from app.database import Achievement, HeroAchievement

        if amount <= 0:
            return []

        await AchievementTracker.ensure_definitions(session)

        definitions = achievements_by_metric(metric)
        if not definitions:
            return []

        now = datetime.utcnow().isoformat()
        unlocked: List[AchievementDefinition] = []

        achievement_rows = await session.execute(
            select(Achievement).where(Achievement.code.in_([d.code for d in definitions]))
        )
        achievement_map = {row.code: row for row in achievement_rows.scalars().all()}

        for definition in definitions:
            achievement = achievement_map.get(definition.code)
            if not achievement:
                continue

            hero_achievement_row = await session.execute(
                select(HeroAchievement)
                .where(HeroAchievement.hero_id == hero.id)
                .where(HeroAchievement.achievement_id == achievement.id)
            )
            hero_achievement = hero_achievement_row.scalar_one_or_none()

            if not hero_achievement:
                hero_achievement = HeroAchievement(
                    hero_id=hero.id,
                    achievement_id=achievement.id,
                    progress=0,
                    unlocked_at=None,
                    progress_updated_at=now,
                )
                session.add(hero_achievement)

            hero_achievement.progress += amount
            hero_achievement.progress_updated_at = now

            if not hero_achievement.unlocked_at and hero_achievement.progress >= definition.target_value:
                hero_achievement.unlocked_at = now
                unlocked.append(definition)

        await session.commit()
        return unlocked

    @staticmethod
    async def get_progress(session: AsyncSession, hero) -> List[AchievementProgress]:
        """Return full achievements progress list for the hero."""
        from app.database import Achievement, HeroAchievement

        await AchievementTracker.ensure_definitions(session)

        # Load hero achievement rows
        rows = await session.execute(
            select(HeroAchievement, Achievement)
            .join(Achievement, HeroAchievement.achievement_id == Achievement.id)
            .where(HeroAchievement.hero_id == hero.id)
        )
        progress_map = {
            achievement.code: (
                hero_achievement.progress,
                bool(hero_achievement.unlocked_at),
                hero_achievement.unlocked_at,
            )
            for hero_achievement, achievement in rows.all()
        }

        result: List[AchievementProgress] = []
        for definition in sorted(all_achievements(), key=lambda d: (d.order, d.target_value, d.code)):
            progress_entry = progress_map.get(definition.code)
            if progress_entry:
                progress_value, unlocked_flag, unlocked_at = progress_entry
                result.append(
                    AchievementProgress(
                        definition=definition,
                        progress=progress_value,
                        unlocked=unlocked_flag,
                        target_value=definition.target_value,
                        unlocked_at=unlocked_at,
                    )
                )
            else:
                result.append(
                    AchievementProgress(
                        definition=definition,
                        progress=0,
                        unlocked=False,
                        target_value=definition.target_value,
                        unlocked_at=None,
                    )
                )

        return result

    @staticmethod
    def format_unlock_message(unlocked: Iterable[AchievementDefinition]) -> str:
        """Create a user-facing message for unlocked achievements."""
        unlocked = list(unlocked)
        if not unlocked:
            return ""

        lines = ["🏅 <b>Нове досягнення!</b>"]
        for definition in unlocked:
            lines.append(f"{definition.icon} <b>{definition.name}</b>")
            lines.append(f"{definition.description}")
        return "\n".join(lines)
