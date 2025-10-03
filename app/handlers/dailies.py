"""Handlers for daily and weekly task progress."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database import get_db_session, get_hero_for_telegram
from models.daily_tasks import DailyTaskTracker


dailies_router = Router()


def _format_progress_bar(current: int, target: int, length: int = 12) -> str:
    target = max(1, target)
    ratio = min(1.0, current / target)
    filled = max(0, min(length, int(round(ratio * length))))
    bar = "█" * filled + "·" * (length - filled)
    return f"[{bar}] {current}/{target}"


def _format_reset_line(reset_ts: str | None, frequency: str) -> str:
    if not reset_ts:
        return "Немає даних про останнє оновлення"
    try:
        reset_dt = datetime.fromisoformat(reset_ts)
    except ValueError:
        return "Немає даних про останнє оновлення"

    if frequency == "daily":
        next_reset = reset_dt + timedelta(days=1)
    else:
        # Align to Monday next week based on stored timestamp
        next_reset = (reset_dt + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

    next_reset = next_reset.astimezone(timezone.utc)
    return f"Наступне оновлення: {next_reset.strftime('%d.%m %H:%M')} UTC"


def _build_tasks_section(title: str, tasks, reset_line: str) -> str:
    lines = [f"{title}", reset_line]
    for entry in tasks:
        status_icon = "✅" if entry.completed else "🔸"
        lines.append(
            f"{status_icon} {entry.definition.icon} <b>{entry.definition.name}</b>"
        )
        lines.append(entry.definition.description)
        if entry.completed:
            if entry.completed_at:
                lines.append(f"🏁 Завершено: {entry.completed_at}")
        else:
            lines.append(
                f"{_format_progress_bar(entry.progress, entry.definition.target)}"
            )
        lines.append("")
    return "\n".join(lines).strip()


async def _render_tasks(hero) -> str:
    async for session in get_db_session():
        daily = await DailyTaskTracker.get_progress(session, hero, "daily")
        weekly = await DailyTaskTracker.get_progress(session, hero, "weekly")
        daily_reset = hero.daily_reset_at
        weekly_reset = hero.weekly_reset_at
        break

    daily_block = _build_tasks_section(
        "🗓️ <b>Щоденні завдання</b>",
        daily,
        _format_reset_line(daily_reset, "daily"),
    )
    weekly_block = _build_tasks_section(
        "📅 <b>Тижневі завдання</b>",
        weekly,
        _format_reset_line(weekly_reset, "weekly"),
    )

    return f"{daily_block}\n\n{weekly_block}"


def _tasks_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Оновити", callback_data="dailies_refresh")]
        ]
    )


def _fallback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔄 Спробувати ще раз", callback_data="dailies_refresh")]]
    )


@dailies_router.message(Command("dailies"))
@dailies_router.message(Command("tasks"))
async def dailies_command(message: Message) -> None:
    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, message.from_user.id)
        if not hero:
            await message.answer("❌ Спершу створіть героя командою /create_hero.")
            return
        await DailyTaskTracker.reset_if_needed(session, hero)
        text = await _render_tasks(hero)
        await message.answer(text, reply_markup=_tasks_keyboard())
        return


@dailies_router.callback_query(lambda call: call.data == "dailies_refresh")
async def dailies_refresh(callback: CallbackQuery) -> None:
    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.message.edit_text(
                "❌ Спершу створіть героя командою /create_hero.",
                reply_markup=_fallback_keyboard()
            )
            await callback.answer()
            return
        await DailyTaskTracker.reset_if_needed(session, hero)
        text = await _render_tasks(hero)
        try:
            await callback.message.edit_text(text, reply_markup=_tasks_keyboard())
        except Exception:
            await callback.message.answer(text, reply_markup=_tasks_keyboard())
        await callback.answer("Оновлено! ✅")
        return
