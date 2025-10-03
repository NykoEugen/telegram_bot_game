"""Profile handler exposing hero achievements and progress."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database import (
    get_db_session,
    get_user_by_telegram_id,
    get_hero_by_user_id,
    get_hero_class_by_id,
)
from app.core.hero_system import HeroCalculator
from models.character_ach import AchievementTracker

profile_router = Router()


def _format_progress_bar(current: int, target: int, length: int = 12) -> str:
    """Render a simple text progress bar."""
    target = max(1, target)
    ratio = min(1.0, current / target)
    filled = max(0, min(length, int(round(ratio * length))))
    bar = "█" * filled + "·" * (length - filled)
    return f"[{bar}] {current}/{target}"


@profile_router.message(Command("profile"))
async def profile_command(message: Message) -> None:
    """Show hero profile with achievements list."""
    async for session in get_db_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Користувач не знайдений. Спершу використайте /start.")
            return

        hero = await get_hero_by_user_id(session, user.id)
        if not hero:
            await message.answer("👤 У вас ще немає героя. Створіть його командою /create_hero.")
            return

        hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
        if not hero_class:
            await message.answer("❌ Помилка: клас героя не знайдений.")
            return

        hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
        achievements = await AchievementTracker.get_progress(session, hero)
        break

    header = (
        f"👤 <b>{hero.name}</b>\n"
        f"⚔️ Клас: {hero_class.name}\n"
        f"📊 Рівень: {hero.level}\n"
        f"⭐ Досвід: {hero_stats.experience}/{hero_stats.xp_to_next}\n"
        f"✨ Вільні характеристики: {hero_stats.attribute_points} | Таланти: {hero_stats.talent_points}\n\n"
    )

    achievement_lines: list[str] = []
    for entry in sorted(achievements, key=lambda item: (item.unlocked is False, item.definition.order, item.target_value)):
        status_icon = "✅" if entry.unlocked else "🔒"
        description_lines = [
            f"{status_icon} {entry.definition.icon} <b>{entry.definition.name}</b>"
        ]

        if entry.unlocked:
            description_lines.append("🏁 Виконано")
            if entry.unlocked_at:
                description_lines.append(f"📅 Відкрито: {entry.unlocked_at}")
        else:
            bar = _format_progress_bar(entry.progress, entry.target_value)
            description_lines.append(f"{bar} ({entry.completion_percent}%)")

        description_lines.append(entry.definition.description)
        achievement_lines.append("\n".join(description_lines))

    achievements_block = "🏅 <b>Досягнення героя</b>\n\n" + "\n\n".join(achievement_lines)

    await message.answer(header + achievements_block)
