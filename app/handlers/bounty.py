"""Handlers for repeatable bounty board."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold, hitalic

from app.core.bounties import BountyGenerator, ensure_active_bounties, serialize_active_bounty
from app.database import (
    AsyncSessionLocal,
    claim_bounty_for_hero,
    complete_bounty_for_hero,
    get_current_active_bounties,
    get_hero_for_telegram,
)
from app.keyboards import BountyKeyboardBuilder
from app.services.progression import record_progress_messages


bounty_router = Router()


async def _load_bounties(session, desired_count: int = 3) -> List[Dict[str, object]]:
    generator = BountyGenerator()
    active_rows = await ensure_active_bounties(session, generator=generator, desired_count=desired_count)
    return [await serialize_active_bounty(row) for row in active_rows]


def _format_bounty_card(bounty: Dict[str, object]) -> str:
    payload = bounty.get('payload', {})
    title = payload.get('title', 'Bounty Assignment')
    description = payload.get('description', 'Complete the task.')
    location = payload.get('location', 'Unknown Location')
    target = payload.get('target', 'Unknown Target')
    rewards = payload.get('rewards', {})

    lines = [
        f"{hbold(title)}",
        description,
        "",
        f"📍 Локація: {location}",
        f"🎯 Ціль: {target}",
    ]

    if rewards:
        lines.append("")
        lines.append(hbold("Нагорода"))
        for key, value in rewards.items():
            lines.append(f"- {key}: {value}")

    expires_at = bounty.get('expires_at')
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at)
            lines.append("")
            lines.append(f"⏳ Доступно до: {exp_dt.strftime('%d.%m %H:%M')} UTC")
        except ValueError:
            pass

    return "\n".join(lines)


@bounty_router.message(Command("bounties"))
async def command_bounties(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        hero = await get_hero_for_telegram(session, message.from_user.id)
        if not hero:
            await message.answer("❌ Спершу створіть героя командою /create_hero.")
            return

        boards = await _load_bounties(session)
        text_lines = [hbold("🎯 Дошка завдань"), "Оберіть винагороду, щоб дізнатись деталі."]
        await message.answer(
            "\n".join(text_lines),
            reply_markup=BountyKeyboardBuilder.bounty_list_keyboard(boards)
        )


@bounty_router.callback_query(F.data == "bounty_refresh")
async def callback_bounty_refresh(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.answer("Створіть героя, щоб бачити винагороди", show_alert=True)
            return

        boards = await _load_bounties(session)
        text_lines = [hbold("🎯 Дошка завдань"), "Оберіть винагороду, щоб дізнатись деталі."]
        await callback.message.edit_text(
            "\n".join(text_lines),
            reply_markup=BountyKeyboardBuilder.bounty_list_keyboard(boards)
        )
        await callback.answer("Оновлено! ✅")


@bounty_router.callback_query(F.data.startswith("bounty_view:"))
async def callback_bounty_view(callback: CallbackQuery) -> None:
    bounty_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.answer("Створіть героя, щоб приймати завдання", show_alert=True)
            return

        active_rows = await get_current_active_bounties(session)
        bounty_map = {row.id: row for row in active_rows}
        row = bounty_map.get(bounty_id)
        if not row:
            await callback.answer("Завдання більше недоступне", show_alert=True)
            return

        bounty = await serialize_active_bounty(row)
        card_text = _format_bounty_card(bounty)

        await callback.message.edit_text(
            card_text,
            reply_markup=BountyKeyboardBuilder.bounty_detail_keyboard(bounty_id, accepted=False)
        )
        await callback.answer()


@bounty_router.callback_query(F.data.startswith("bounty_accept:"))
async def callback_bounty_accept(callback: CallbackQuery) -> None:
    bounty_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.answer("Створіть героя, щоб приймати завдання", show_alert=True)
            return

        progress = await claim_bounty_for_hero(session, hero.id, bounty_id)
        await callback.answer("Завдання прийнято!", show_alert=True)

        active_rows = await get_current_active_bounties(session)
        row = next((entry for entry in active_rows if entry.id == bounty_id), None)
        if not row:
            await callback.message.edit_text("Завдання більше недоступне. Спробуйте інше.")
            return

        bounty = await serialize_active_bounty(row)
        card_text = _format_bounty_card(bounty)
        await callback.message.edit_text(
            card_text,
            reply_markup=BountyKeyboardBuilder.bounty_detail_keyboard(bounty_id, accepted=True)
        )


@bounty_router.callback_query(F.data.startswith("bounty_complete:"))
async def callback_bounty_complete(callback: CallbackQuery) -> None:
    bounty_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.answer("Створіть героя, щоб завершувати завдання", show_alert=True)
            return

        progress = await complete_bounty_for_hero(session, hero.id, bounty_id, success=True)
        if not progress:
            await callback.answer("Не вдалося оновити статус", show_alert=True)
            return

        card_template = [hbold("🏁 Завдання виконано!"), "Звітуйте наставнику для нових доручень."]

        for message_text in await record_progress_messages(hero.id, 'bounties_completed', 1):
            await callback.message.answer(message_text)

        await callback.message.edit_text(
            "\n".join(card_template),
            reply_markup=BountyKeyboardBuilder.bounty_list_keyboard([])
        )
        await callback.answer()


@bounty_router.callback_query(F.data == "bounty_back")
async def callback_bounty_back(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.answer("Створіть героя, щоб бачити завдання", show_alert=True)
            return

        boards = await _load_bounties(session)
        text_lines = [hbold("🎯 Дошка завдань"), "Оберіть винагороду, щоб дізнатись деталі."]
        await callback.message.edit_text(
            "\n".join(text_lines),
            reply_markup=BountyKeyboardBuilder.bounty_list_keyboard(boards)
        )
        await callback.answer()

