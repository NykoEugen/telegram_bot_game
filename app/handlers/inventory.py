"""Handlers for viewing and using inventory items outside of combat."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from app.database import (
    get_db_session,
    get_hero_for_telegram,
    get_hero_by_id,
    get_hero_class_by_id,
    list_hero_inventory,
    get_item_by_code,
    consume_hero_item,
    update_hero,
)
from app.core.hero_system import HeroCalculator
from app.core.item_system import ItemEngine, InventoryItemDefinition, ItemEffectType

logger = logging.getLogger(__name__)

router = Router()


async def _load_inventory_payload(hero_id: int) -> Tuple:
    """Load hero, stats, and item definitions for inventory rendering."""
    async for session in get_db_session():
        hero = await get_hero_by_id(session, hero_id)
        if not hero:
            return None, None, []

        hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
        hero_stats = HeroCalculator.create_hero_stats(hero, hero_class) if hero_class else None

        inventory_entries = await list_hero_inventory(session, hero.id)
        items: List[Tuple[int, InventoryItemDefinition]] = []
        for entry, item_model in inventory_entries:
            definition = ItemEngine.parse_model(item_model)
            items.append((entry.quantity, definition))

        return hero, hero_stats, items

    return None, None, []


async def _build_inventory_message(
    hero_stats,
    items: List[Tuple[int, InventoryItemDefinition]],
    *,
    context: str,
    allow_usage_predicate,
) -> tuple[str, InlineKeyboardBuilder]:
    """Construct inventory message and keyboard for a given context."""
    lines = ["🎒 <b>Інвентар</b>"]
    if hero_stats:
        lines.append(f"❤️ HP: {hero_stats.hp_current}/{hero_stats.hp_max}")
    lines.append("\nОберіть предмет для використання або закрийте меню.")

    builder = InlineKeyboardBuilder()

    usable_count = 0
    for quantity, definition in items:
        if not allow_usage_predicate(definition):
            continue
        usable_count += 1
        lines.append(f"{definition.label} ×{quantity}\n<i>{definition.description}</i>")
        builder.button(
            text=f"{definition.label} ×{quantity}",
            callback_data=f"inventory_use:{context}:{definition.code}"
        )

    if usable_count == 0:
        lines.append("\nНемає доступних предметів для використання у цій ситуації.")

    builder.button(text="❌ Закрити", callback_data=f"inventory_close:{context}")
    builder.adjust(1)

    return "\n\n".join(lines), builder


@router.message(Command("inventory"))
async def inventory_command(message: Message):
    """Show inventory overview to the player."""
    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, message.from_user.id)
        if not hero:
            await message.answer("❌ У вас немає героя. Створіть героя командою /create_hero.")
            return

        break
    else:
        await message.answer("❌ Не вдалося отримати інвентар.")
        return

    hero, hero_stats, items = await _load_inventory_payload(hero.id)
    if not hero:
        await message.answer("❌ Не вдалося отримати інвентар.")
        return

    text, builder = await _build_inventory_message(
        hero_stats=hero_stats,
        items=items,
        context="default",
        allow_usage_predicate=lambda item: item.can_use_outside_combat,
    )

    await message.answer(text, reply_markup=builder.as_markup())


async def build_overworld_inventory_view(
    hero_id: int,
    *,
    context: str = "default"
) -> Optional[tuple[str, InlineKeyboardMarkup]]:
    """Build inventory view suitable for outside of combat usage."""
    hero, hero_stats, items = await _load_inventory_payload(hero_id)
    if not hero:
        return None

    text, builder = await _build_inventory_message(
        hero_stats=hero_stats,
        items=items,
        context=context,
        allow_usage_predicate=lambda item: item.can_use_outside_combat,
    )
    return text, builder.as_markup()


@router.callback_query(F.data.startswith("inventory_close:"))
async def inventory_close_callback(callback: CallbackQuery):
    """Close inventory message."""
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("inventory_use:"))
async def inventory_use_callback(callback: CallbackQuery):
    """Handle using an item from the inventory message."""
    _, context, item_code = callback.data.split(":", maxsplit=2)

    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        if not hero:
            await callback.answer("❌ Героя не знайдено.", show_alert=True)
            return

        hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
        if not hero_class:
            await callback.answer("❌ Клас героя не знайдено.", show_alert=True)
            return

        hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
        item_model = await get_item_by_code(session, item_code)
        if not item_model:
            await callback.answer("Предмет не знайдено.", show_alert=True)
            return

        definition = ItemEngine.parse_model(item_model)
        if not definition.can_use_outside_combat:
            await callback.answer("Цей предмет не можна використати зараз.", show_alert=True)
            return

        outcome = ItemEngine.apply_effect(
            definition,
            hp_current=hero_stats.hp_current,
            hp_max=hero_stats.hp_max,
        )

        if (
            definition.effect.effect_type == ItemEffectType.HEAL
            and outcome.hp_restored <= 0
        ):
            await callback.answer(outcome.description, show_alert=True)
            return

        consumed = await consume_hero_item(session, hero.id, definition.code)
        if not consumed:
            await callback.answer("Немає такого предмета в інвентарі.", show_alert=True)
            return

        hero.current_hp = outcome.new_hp or hero.current_hp
        await update_hero(session, hero)
        break

    hero, hero_stats, items = await _load_inventory_payload(hero.id)
    if not hero:
        await callback.answer("❌ Героя не знайдено.", show_alert=True)
        return

    text, builder = await _build_inventory_message(
        hero_stats=hero_stats,
        items=items,
        context=context,
        allow_usage_predicate=lambda item: item.can_use_outside_combat,
    )
    reply_markup = builder.as_markup()
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=reply_markup)
    await callback.answer("Предмет використано!")
    return

    await callback.answer("❌ Не вдалося використати предмет.", show_alert=True)
