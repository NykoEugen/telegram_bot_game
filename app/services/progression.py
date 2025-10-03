"""Shared helpers for recording progression metrics (achievements, dailies)."""

from __future__ import annotations

from typing import List

from app.database import get_db_session, get_hero_by_id
from models.character_ach import AchievementTracker
from models.daily_tasks import DailyTaskTracker


async def record_progress_messages(hero_id: int, metric: str, amount: int = 1) -> List[str]:
    """Update metric-driven progression and return user-facing messages."""
    unlocked_achievements = []
    completed_daily = []
    completed_weekly = []

    async for session in get_db_session():
        hero = await get_hero_by_id(session, hero_id)
        if not hero:
            break

        unlocked_achievements = await AchievementTracker.record_metric(session, hero, metric, amount)
        daily, weekly = await DailyTaskTracker.record_metric(session, hero, metric, amount)
        completed_daily.extend(daily)
        completed_weekly.extend(weekly)
        break

    messages: List[str] = []

    if unlocked_achievements:
        achievement_message = AchievementTracker.format_unlock_message(unlocked_achievements)
        if achievement_message:
            messages.append(achievement_message)

    if completed_daily:
        lines = ["✅ <b>Щоденне завдання виконано!</b>"]
        for definition in completed_daily:
            lines.append(f"{definition.icon} <b>{definition.name}</b>")
            lines.append(definition.description)
        messages.append("\n".join(lines))

    if completed_weekly:
        lines = ["🌟 <b>Тижневе завдання завершено!</b>"]
        for definition in completed_weekly:
            lines.append(f"{definition.icon} <b>{definition.name}</b>")
            lines.append(definition.description)
        messages.append("\n".join(lines))

    return messages
