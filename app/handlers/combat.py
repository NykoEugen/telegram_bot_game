"""
Combat handlers for Telegram bot commands and callbacks.
"""

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import (
    get_db_session,
    get_hero_by_user_id,
    get_hero_class_by_id,
    get_monster_by_id,
    get_monster_class_by_id,
    update_hero,
    add_hero_experience,
    list_hero_inventory,
    get_item_by_code,
    consume_hero_item,
    get_hero_by_id,
    get_hero_for_telegram,
)
from app.core.hero_system import HeroCalculator
from app.core.monster_system import MonsterCalculator
from app.core.combat_system import combat_engine, CombatAction, CombatResult
from app.core.item_system import ItemEngine, InventoryItemDefinition, ItemEffectType
from app.handlers.graph_quest import GraphQuestManager
from app.handlers.inventory import build_overworld_inventory_view
from app.keyboards import get_combat_keyboard, get_main_menu_keyboard
from models.character_ach import AchievementTracker

logger = logging.getLogger(__name__)

router = Router()


QUEST_ENCOUNTER_BONUS_XP = 0.3  # 30% bonus exp for quest combat victories
QUEST_ENCOUNTER_BONUS_GOLD = 0.25  # 25% bonus gold for quest combat victories


async def _replace_message(
    callback: CallbackQuery,
    text: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Safely replace callback message text and markup, falling back to new message."""
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=keyboard)


async def _record_and_notify_achievements(
    callback: CallbackQuery,
    hero_id: int,
    metric: str,
    amount: int = 1,
) -> None:
    """Increment an achievement metric and notify the player if something unlocked."""
    unlocked = []
    async for session in get_db_session():
        hero = await get_hero_by_id(session, hero_id)
        if not hero:
            break
        unlocked = await AchievementTracker.record_metric(session, hero, metric, amount)
        break

    if unlocked:
        message = AchievementTracker.format_unlock_message(unlocked)
        if message:
            await callback.message.answer(message)


class CombatStates(StatesGroup):
    """States for combat flow."""
    IN_COMBAT = State()
    CHOOSING_ITEM = State()


async def _show_combat_inventory(
    callback: CallbackQuery,
    state: FSMContext,
    combat_state
) -> None:
    """Display hero inventory options during combat."""
    inventory_entries = []

    async for session in get_db_session():
        inventory_entries = await list_hero_inventory(session, combat_state.hero_id)
        break

    usable_items: list[tuple[int, InventoryItemDefinition]] = []
    for inventory_item, item_model in inventory_entries:
        definition = ItemEngine.parse_model(item_model)
        if definition.can_use_in_combat:
            usable_items.append((inventory_item.quantity, definition))

    builder = InlineKeyboardBuilder()
    if usable_items:
        lines = ["🎒 <b>Інвентар (бій)</b>", "Оберіть предмет для використання:"]
        for quantity, definition in usable_items:
            lines.append(f"{definition.label} ×{quantity}\n<i>{definition.description}</i>")
            builder.button(
                text=f"{definition.label} ×{quantity}",
                callback_data=f"combat_use_item:{definition.code}"
            )
        message_text = "\n\n".join(lines)
    else:
        message_text = (
            "🎒 <b>Інвентар (бій)</b>\n\n"
            "У вас немає предметів, які можна використати під час бою."
        )

    builder.button(text="⬅️ Назад", callback_data="combat_back")
    builder.adjust(1)

    await state.set_state(CombatStates.CHOOSING_ITEM)
    await callback.message.edit_text(message_text, reply_markup=builder.as_markup())
    await callback.answer()


def _compose_combat_screen(combat_state) -> str:
    """Compose combat status text with recent log entries."""
    status_text = combat_engine.format_combat_status(combat_state)
    recent_log = combat_state.combat_log[-3:] if len(combat_state.combat_log) > 3 else combat_state.combat_log
    log_text = "\n".join(recent_log) if recent_log else "Бій щойно почався."
    return f"{status_text}\n\n📜 <b>Останні дії:</b>\n{log_text}"


async def _send_inventory_after_flee(callback: CallbackQuery, hero_id: int) -> None:
    """Send inventory overview to encourage healing after a successful flee."""
    inventory_view = await build_overworld_inventory_view(hero_id, context="post_flee")
    if not inventory_view:
        return

    text, markup = inventory_view
    try:
        await callback.message.answer(text, reply_markup=markup)
    except Exception as exc:  # pragma: no cover - Telegram API errors
        logger.warning("Failed to send inventory after flee: %s", exc)


@router.message(Command("fight"))
async def start_fight_command(message: Message, state: FSMContext):
    """Start a fight with a random monster."""
    user_id = message.from_user.id
    
    # Check if user is already in combat
    if combat_engine.get_combat_state(user_id):
        await message.answer("⚔️ Ви вже в бою! Завершіть поточний бій перед початком нового.")
        return
    
    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, user_id)
        if not hero:
            await message.answer("❌ У вас немає героя! Створіть героя командою /create_hero")
            return
        
        # Get hero class
        hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
        if not hero_class:
            await message.answer("❌ Помилка: клас героя не знайдено!")
            return
        
        # Get a random monster (for now, we'll create a simple one)
        # In a real implementation, you'd have a monster spawning system
        from app.initializers.monsters import create_sample_monster
        monster = await create_sample_monster(session)
        monster_class = await get_monster_class_by_id(session, monster.monster_class_id)
        
        if not monster_class:
            await message.answer("❌ Помилка: клас монстра не знайдено!")
            return
        
        # Start combat
        combat_state = combat_engine.start_combat(user_id, hero, hero_class, monster, monster_class)
        
        # Set state
        await state.set_state(CombatStates.IN_COMBAT)
        await state.update_data(monster_id=monster.id, hero_id=hero.id)
        
        # Send combat status
        status_text = combat_engine.format_combat_status(combat_state)
        await message.answer(
            status_text,
            reply_markup=get_combat_keyboard()
        )
        break


@router.callback_query(F.data.startswith("combat_"), StateFilter(CombatStates.IN_COMBAT))
async def handle_combat_action(callback: CallbackQuery, state: FSMContext):
    """Handle combat action callbacks."""
    user_id = callback.from_user.id
    action_data = callback.data.split("_")[1]
    
    # Check if user is still in combat
    combat_state = combat_engine.get_combat_state(user_id)
    if not combat_state:
        await callback.answer("❌ Бій вже завершено!")
        await state.clear()
        return

    # Map callback data to combat actions
    action_map = {
        "attack": CombatAction.ATTACK,
        "magic": CombatAction.MAGIC,
        "defend": CombatAction.DEFEND,
        "flee": CombatAction.FLEE
    }

    if action_data == "inventory":
        await _show_combat_inventory(callback, state, combat_state)
        return

    if action_data not in action_map:
        await callback.answer("❌ Невідома дія!")
        return
    
    action = action_map[action_data]
    state_data = await state.get_data()
    
    # Execute hero action
    hero_result = combat_engine.execute_hero_action(user_id, action)
    if not hero_result:
        await callback.answer("❌ Помилка виконання дії!")
        return

    # Add result to combat log
    combat_state.combat_log.append(hero_result.message)

    if hero_result.is_critical:
        await _record_and_notify_achievements(callback, combat_state.hero_id, 'critical_hits', 1)

    # Apply flee penalties when escape fails during quests
    if (
        action == CombatAction.FLEE
        and state_data.get('source') == 'graph_quest'
        and "Не вдалося втекти" in hero_result.message
        and not state_data.get('flee_penalty_applied')
    ):
        quest_id = state_data.get('quest_id')
        if quest_id:
            debuff = {
                'type': 'flee_failure',
                'atk_multiplier': 0.85,
                'dodge_penalty': 0.15,
                'hp_penalty_percent': 0.1,
                'message': '⚠️ Невдала втеча послабила героя!'
            }
            await GraphQuestManager.apply_hero_debuff(user_id, quest_id, debuff)

            combat_state.hero_stats.atk = int(combat_state.hero_stats.atk * debuff['atk_multiplier'])
            combat_state.hero_stats.mag = int(combat_state.hero_stats.mag * debuff['atk_multiplier'])
            combat_state.hero_stats.crit_chance = max(
                0.0,
                combat_state.hero_stats.crit_chance * debuff['atk_multiplier']
            )
            combat_state.hero_stats.dodge = max(
                0.0,
                combat_state.hero_stats.dodge * (1 - debuff['dodge_penalty'])
            )
            combat_state.combat_log.append('⚠️ Герой ослаблений після невдалої втечі!')
            await state.update_data(flee_penalty_applied=True)
    
    # Check if combat ended after hero action
    combat_result = combat_engine.check_combat_end(user_id)
    if combat_result == CombatResult.HERO_WIN:
        await handle_combat_victory(callback, state, combat_state)
        return
    elif combat_result == CombatResult.MONSTER_WIN:
        await handle_combat_defeat(callback, state, combat_state)
        return
    elif combat_result == CombatResult.HERO_FLEE:
        await handle_combat_flee(callback, state, combat_state)
        return
    
    # Execute monster action
    monster_result = combat_engine.execute_monster_action(user_id)
    if monster_result:
        combat_state.combat_log.append(monster_result.message)
    
    # Check if combat ended after monster action
    combat_result = combat_engine.check_combat_end(user_id)
    if combat_result == CombatResult.MONSTER_WIN:
        await handle_combat_defeat(callback, state, combat_state)
        return
    
    # Increment turn
    combat_state.turn += 1
    combat_state.hero_defending = False
    combat_state.monster_defending = False

    # Update combat status
    full_text = _compose_combat_screen(combat_state)

    await callback.message.edit_text(
        full_text,
        reply_markup=get_combat_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "combat_back", StateFilter(CombatStates.CHOOSING_ITEM))
async def handle_combat_back(callback: CallbackQuery, state: FSMContext):
    """Return from inventory view back to combat actions."""
    user_id = callback.from_user.id
    combat_state = combat_engine.get_combat_state(user_id)

    if not combat_state:
        await callback.answer("Бій вже завершено.", show_alert=True)
        await state.clear()
        return

    await state.set_state(CombatStates.IN_COMBAT)
    full_text = _compose_combat_screen(combat_state)

    await callback.message.edit_text(
        full_text,
        reply_markup=get_combat_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("combat_use_item:"), StateFilter(CombatStates.CHOOSING_ITEM))
async def handle_combat_use_item(callback: CallbackQuery, state: FSMContext):
    """Apply selected inventory item and resume combat flow."""
    user_id = callback.from_user.id
    combat_state = combat_engine.get_combat_state(user_id)

    if not combat_state:
        await callback.answer("Бій вже завершено.", show_alert=True)
        await state.clear()
        return

    _, item_code = callback.data.split(":", maxsplit=1)

    item_model = None
    async for session in get_db_session():
        item_model = await get_item_by_code(session, item_code)
        break

    if not item_model:
        await callback.answer("Предмет не знайдено.", show_alert=True)
        return

    definition = ItemEngine.parse_model(item_model)
    if not definition.can_use_in_combat:
        await callback.answer("Цей предмет не можна використати під час бою.", show_alert=True)
        return

    outcome = ItemEngine.apply_effect(
        definition,
        hp_current=combat_state.hero_hp,
        hp_max=combat_state.hero_stats.hp_max,
    )

    if (
        definition.effect.effect_type == ItemEffectType.HEAL
        and outcome.hp_restored <= 0
    ):
        await callback.answer(outcome.description, show_alert=True)
        return

    async for session in get_db_session():
        consumed = await consume_hero_item(session, combat_state.hero_id, definition.code)
        if not consumed:
            await callback.answer("Немає такого предмета в інвентарі.", show_alert=True)
            return

        hero = await get_hero_by_id(session, combat_state.hero_id)
        if hero and outcome.new_hp is not None:
            hero.current_hp = outcome.new_hp
            await update_hero(session, hero)
        break

    combat_state.hero_hp = outcome.new_hp or combat_state.hero_hp
    combat_state.hero_stats.hp_current = combat_state.hero_hp
    combat_state.combat_log.append(outcome.as_log_entry(f"{definition.label}"))

    await state.set_state(CombatStates.IN_COMBAT)

    # Monster takes its turn after item usage
    combat_state.hero_defending = False
    combat_state.monster_defending = False

    monster_result = combat_engine.execute_monster_action(user_id)
    if monster_result:
        combat_state.combat_log.append(monster_result.message)

    combat_result = combat_engine.check_combat_end(user_id)
    if combat_result == CombatResult.MONSTER_WIN:
        await handle_combat_defeat(callback, state, combat_state)
        return

    combat_state.turn += 1

    full_text = _compose_combat_screen(combat_state)

    await callback.message.edit_text(
        full_text,
        reply_markup=get_combat_keyboard()
    )
    await callback.answer("Предмет використано!")

async def handle_combat_victory(callback: CallbackQuery, state: FSMContext, combat_state):
    """Handle combat victory."""
    user_id = callback.from_user.id
    state_data = await state.get_data()

    # Calculate rewards
    rewards = combat_engine.get_combat_rewards(combat_state)

    quest_mode = state_data.get('source') == 'graph_quest'
    bonus_summary = ""
    quest_id = state_data.get('quest_id') if quest_mode else None
    node_id = state_data.get('node_id') if quest_mode else None

    if quest_mode and quest_id is not None and node_id is not None:
        bonus_xp = max(1, int(rewards['experience'] * QUEST_ENCOUNTER_BONUS_XP))
        bonus_gold = max(1, int(rewards['gold'] * QUEST_ENCOUNTER_BONUS_GOLD))
        rewards['experience'] += bonus_xp
        rewards['gold'] += bonus_gold
        bonus_summary = f" (включно з бонусом {bonus_xp} XP / {bonus_gold} золота за квест)"

    # Update hero with (possibly boosted) rewards
    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, user_id)
        if hero:
            hero = await add_hero_experience(session, hero, rewards['experience'])
            hero.current_hp = combat_state.hero_hp
            await update_hero(session, hero)
        break

    await _record_and_notify_achievements(callback, combat_state.hero_id, 'combat_victories', 1)
    if getattr(combat_state.monster_stats, 'difficulty', None) == 'boss':
        await _record_and_notify_achievements(callback, combat_state.hero_id, 'boss_victories', 1)

    if quest_mode and quest_id is not None and node_id is not None:
        summary = (
            f"🏆 <b>Нагороди:</b>\n"
            f"⭐ Досвід: +{rewards['experience']}{bonus_summary}\n"
            f"💰 Золото: +{rewards['gold']}\n"
            f"❤️ HP після бою: {combat_state.hero_hp}/{combat_state.hero_stats.hp_max}"
        )

        outcome = await GraphQuestManager.resolve_encounter_outcome(
            user_id=user_id,
            quest_id=quest_id,
            node_id=node_id,
            outcome='victory',
            combat_summary=summary
        )

        combat_engine.end_combat(user_id)
        await state.clear()

        if outcome:
            await _replace_message(callback, outcome['text'], outcome['keyboard'])
        else:
            await _replace_message(
                callback,
                "🎉 Перемога! Продовжуйте пригоду.",
                get_main_menu_keyboard(),
            )
        await callback.answer()
        return

    victory_text = f"""
🎉 <b>ПЕРЕМОГА!</b>

Ви перемогли {combat_state.monster_stats.monster_type if hasattr(combat_state.monster_stats, 'monster_type') else 'монстра'}!

🏆 <b>Нагороди:</b>
⭐ Досвід: +{rewards['experience']}
💰 Золото: +{rewards['gold']}

❤️ HP після бою: {combat_state.hero_hp}/{combat_state.hero_stats.hp_max}
"""

    await _replace_message(
        callback,
        victory_text,
        get_main_menu_keyboard(),
    )

    # Clear combat state
    combat_engine.end_combat(user_id)
    await state.clear()
    await callback.answer()


async def handle_combat_defeat(callback: CallbackQuery, state: FSMContext, combat_state):
    """Handle combat defeat."""
    user_id = callback.from_user.id
    state_data = await state.get_data()

    # Update hero's HP to 1 (not dead, just defeated)
    async for session in get_db_session():
        hero = await get_hero_for_telegram(session, user_id)
        if hero:
            hero.current_hp = 1  # Leave hero with 1 HP
            await update_hero(session, hero)
        break

    if state_data.get('source') == 'graph_quest':
        quest_id = state_data.get('quest_id')
        node_id = state_data.get('node_id')

        outcome = await GraphQuestManager.resolve_encounter_outcome(
            user_id=user_id,
            quest_id=quest_id,
            node_id=node_id,
            outcome='defeat'
        )

        combat_engine.end_combat(user_id)
        await state.clear()

        if outcome:
            await _replace_message(callback, outcome['text'], outcome['keyboard'])
        else:
            await _replace_message(
                callback,
                "💀 Ви зазнали поразки. Відновіться перед новою спробою.",
                get_main_menu_keyboard(),
            )
        await callback.answer()
        return

    defeat_text = f"""
💀 <b>ПОРАЗКА!</b>

Ви були переможені {combat_state.monster_stats.monster_type if hasattr(combat_state.monster_stats, 'monster_type') else 'монстром'}!

🏥 Ваш герой втратив свідомість і був доставлений до найближчого міста.
❤️ HP відновлено до 1.

Спробуйте ще раз, коли будете готові!
"""

    await _replace_message(
        callback,
        defeat_text,
        get_main_menu_keyboard(),
    )

    # Clear combat state
    combat_engine.end_combat(user_id)
    await state.clear()
    await callback.answer()


async def handle_combat_flee(callback: CallbackQuery, state: FSMContext, combat_state):
    """Handle successful flee from combat."""
    state_data = await state.get_data()

    if state_data.get('source') == 'graph_quest':
        quest_id = state_data.get('quest_id')
        node_id = state_data.get('node_id')

        debuff = {
            'type': 'flee_exhaustion',
            'atk_multiplier': 0.9,
            'dodge_penalty': 0.1,
            'hp_penalty_percent': 0.15,
            'message': '😫 Герой виснажений після втечі — характеристики тимчасово знижені.'
        }
        await GraphQuestManager.apply_hero_debuff(callback.from_user.id, quest_id, debuff)

        failure_note = "🏃 Ви втекли з бою. Герой виснажений і повернувся до попередньої локації."
        outcome = await GraphQuestManager.resolve_encounter_outcome(
            user_id=callback.from_user.id,
            quest_id=quest_id,
            node_id=node_id,
            outcome='flee_success',
            failure_note=failure_note
        )

        combat_engine.end_combat(callback.from_user.id)
        await state.clear()

        if outcome:
            await _replace_message(callback, outcome['text'], outcome['keyboard'])
        else:
            await _replace_message(
                callback,
                "🏃 Ви відступили. Поверніться, коли будете готові продовжити пригоду.",
                get_main_menu_keyboard(),
            )
        await _send_inventory_after_flee(callback, combat_state.hero_id)
        await callback.answer()
        return

    flee_text = f"""
🏃 <b>ВТЕЧА!</b>

Ви успішно втекли з бою!

❤️ HP після втечі: {combat_state.hero_hp}/{combat_state.hero_stats.hp_max}

Іноді розумність важливіша за хоробрість!
"""

    await _replace_message(
        callback,
        flee_text,
        get_main_menu_keyboard(),
    )

    # Clear combat state
    combat_engine.end_combat(callback.from_user.id)
    await state.clear()
    await _send_inventory_after_flee(callback, combat_state.hero_id)
    await callback.answer()


@router.message(Command("combat_status"))
async def combat_status_command(message: Message, state: FSMContext):
    """Check current combat status."""
    user_id = message.from_user.id
    
    combat_state = combat_engine.get_combat_state(user_id)
    if not combat_state:
        await message.answer("❌ Ви не в бою зараз.")
        return
    
    status_text = combat_engine.format_combat_status(combat_state)
    
    # Show recent combat log
    recent_log = combat_state.combat_log[-5:] if len(combat_state.combat_log) > 5 else combat_state.combat_log
    log_text = "\n".join(recent_log) if recent_log else "Бій щойно почався."
    
    full_text = f"{status_text}\n\n📜 <b>Історія бою:</b>\n{log_text}"
    
    await message.answer(
        full_text,
        reply_markup=get_combat_keyboard()
    )


@router.message(Command("end_combat"))
async def end_combat_command(message: Message, state: FSMContext):
    """Force end current combat."""
    user_id = message.from_user.id
    
    combat_state = combat_engine.get_combat_state(user_id)
    if not combat_state:
        await message.answer("❌ Ви не в бою зараз.")
        return
    
    # End combat
    combat_engine.end_combat(user_id)
    await state.clear()
    
    await message.answer(
        "⚔️ Бій примусово завершено.",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(StateFilter(CombatStates.IN_COMBAT))
async def combat_state_handler(message: Message):
    """Handle messages while in combat state."""
    await message.answer(
        "⚔️ Ви в бою! Використовуйте кнопки для вибору дій або команду /end_combat для завершення бою."
    )
