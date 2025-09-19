"""
Hero system handlers for Telegram bot.
"""

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    get_db_session, create_user, get_user_by_telegram_id, 
    create_hero, get_hero_by_user_id, get_hero_class_by_id, get_all_hero_classes,
    create_hero_class, get_hero_class_by_name, Hero, HeroClass
)
from hero_system import HeroCalculator, HeroClasses

logger = logging.getLogger(__name__)

# Create router for hero handlers
hero_router = Router()


class HeroCreationStates(StatesGroup):
    """States for hero creation process."""
    choosing_class = State()
    entering_name = State()
    confirming_creation = State()


@hero_router.message(Command("hero"))
async def hero_command(message: Message, state: FSMContext):
    """Handle /hero command - show hero info or start creation."""
    async for session in get_db_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Користувач не знайдений. Використайте /start для реєстрації.")
            return
        
        hero = await get_hero_by_user_id(session, user.id)
        
        if hero:
            # Show existing hero info
            hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
            if hero_class:
                hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
                stats_text = HeroCalculator.format_stats_display(hero_stats, hero_class)
                
                # Create keyboard with exit button
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚪 Закрити", callback_data="close_hero_info")]
                ])
                
                await message.answer(stats_text, reply_markup=keyboard)
            else:
                await message.answer("❌ Помилка: клас героя не знайдений.")
        else:
            # Start hero creation
            await start_hero_creation(message, state)


@hero_router.message(Command("create_hero"))
async def create_hero_command(message: Message, state: FSMContext):
    """Handle /create_hero command - start hero creation process."""
    async for session in get_db_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Користувач не знайдений. Використайте /start для реєстрації.")
            return
        
        hero = await get_hero_by_user_id(session, user.id)
        
        if hero:
            await message.answer("❌ У вас вже є герой! Використайте /hero для перегляду інформації.")
            return
        
        await start_hero_creation(message, state)


async def show_class_selection_menu(message_or_callback, state: FSMContext):
    """Show class selection menu."""
    await state.set_state(HeroCreationStates.choosing_class)
    logger.info(f"Showing class selection menu for user {message_or_callback.from_user.id}")
    
    # Create keyboard with hero classes
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Get available hero classes
    async for session in get_db_session():
        hero_classes = await get_all_hero_classes(session)
        
        for hero_class in hero_classes:
            button = InlineKeyboardButton(
                text=hero_class.name,
                callback_data=f"choose_class_{hero_class.id}"
            )
            keyboard.inline_keyboard.append([button])
        
        if not hero_classes:
            text = "❌ Немає доступних класів героїв. Зверніться до адміністратора."
            if hasattr(message_or_callback, 'edit_text'):
                try:
                    await message_or_callback.edit_text(text)
                except Exception as e:
                    logger.warning(f"Could not edit message, sending new one: {e}")
                    await message_or_callback.answer(text)
            else:
                await message_or_callback.answer(text)
            return
    
    text = (
        "⚔️ <b>Створення героя</b>\n\n"
        "Оберіть клас для вашого героя:"
    )
    
    if hasattr(message_or_callback, 'edit_text'):
        try:
            await message_or_callback.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Could not edit message, sending new one: {e}")
            await message_or_callback.answer(text, reply_markup=keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)


async def start_hero_creation(message: Message, state: FSMContext):
    """Start hero creation process by showing available classes."""
    await show_class_selection_menu(message, state)


@hero_router.callback_query(F.data.startswith("choose_class_"))
async def choose_hero_class(callback: CallbackQuery, state: FSMContext):
    """Handle hero class selection."""
    class_id = int(callback.data.split("_")[2])
    
    async for session in get_db_session():
        hero_class = await get_hero_class_by_id(session, class_id)
        if not hero_class:
            await callback.answer("❌ Клас не знайдений.")
            return
        
        # Store selected class in state
        await state.update_data(selected_class_id=class_id)
        
        # Show class info with selection buttons
        class_info = HeroCalculator.format_class_info(hero_class)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Вибрати цей клас", callback_data=f"select_class_{class_id}")],
            [InlineKeyboardButton(text="⬅️ Назад до вибору", callback_data="back_to_classes")]
        ])
        
        await callback.message.edit_text(
            f"{class_info}\n\n"
            f"Оберіть дію:",
            reply_markup=keyboard
        )
        await callback.answer()


@hero_router.callback_query(F.data.startswith("select_class_"))
async def select_hero_class(callback: CallbackQuery, state: FSMContext):
    """Confirm class selection and ask for hero name."""
    class_id = int(callback.data.split("_")[2])
    
    async for session in get_db_session():
        hero_class = await get_hero_class_by_id(session, class_id)
        if not hero_class:
            await callback.answer("❌ Клас не знайдений.")
            return
        
        # Store selected class in state
        await state.update_data(selected_class_id=class_id)
        await state.set_state(HeroCreationStates.entering_name)
        logger.info(f"User {callback.from_user.id} selected class {class_id}, state changed to: {HeroCreationStates.entering_name.state}")
        
        # Ask for hero name
        await callback.message.edit_text(
            f"⚔️ <b>Створення героя</b>\n\n"
            f"Обраний клас: <b>{hero_class.name}</b>\n\n"
            f"✍️ Введіть ім'я для вашого героя:"
        )
        await callback.answer()


@hero_router.callback_query(F.data == "back_to_classes")
async def back_to_class_selection(callback: CallbackQuery, state: FSMContext):
    """Return to class selection menu."""
    await show_class_selection_menu(callback, state)
    await callback.answer()


@hero_router.message(StateFilter(HeroCreationStates.entering_name))
async def enter_hero_name(message: Message, state: FSMContext):
    """Handle hero name input."""
    try:
        logger.info(f"Processing hero name input for user {message.from_user.id}: '{message.text}'")
        name = message.text.strip()
        
        logger.info(f"Hero name validation: length={len(name)}, name='{name}'")
        
        if len(name) < 2:
            logger.info(f"Hero name too short for user {message.from_user.id}")
            await message.answer("❌ Ім'я героя має бути мінімум 2 символи. Повертаємося до вибору класу...")
            await show_class_selection_menu(message, state)
            return
        
        if len(name) > 20:
            logger.info(f"Hero name too long for user {message.from_user.id}")
            await message.answer("❌ Ім'я героя має бути максимум 20 символів. Повертаємося до вибору класу...")
            await show_class_selection_menu(message, state)
            return
        
        logger.info(f"Hero name '{name}' is valid for user {message.from_user.id}")
        
        # Store name and show confirmation
        await state.update_data(hero_name=name)
        await state.set_state(HeroCreationStates.confirming_creation)
        logger.info(f"User {message.from_user.id} entered hero name '{name}', state changed to: {HeroCreationStates.confirming_creation.state}")
        
        # Get class info for confirmation
        data = await state.get_data()
        class_id = data.get('selected_class_id')
        
        async for session in get_db_session():
            hero_class = await get_hero_class_by_id(session, class_id)
            if hero_class:
                class_info = HeroCalculator.format_class_info(hero_class)
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_hero")],
                    [InlineKeyboardButton(text="⬅️ Змінити клас", callback_data="back_to_classes")],
                    [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_hero")]
                ])
                
                await message.answer(
                    f"🎯 <b>Підтвердження створення героя</b>\n\n"
                    f"Ім'я: <b>{name}</b>\n\n"
                    f"{class_info}\n\n"
                    f"Підтвердити створення героя?",
                    reply_markup=keyboard
                )
                logger.info(f"Confirmation message sent to user {message.from_user.id}")
            else:
                logger.error(f"Hero class not found for class_id: {class_id}")
                await message.answer("❌ Помилка: клас героя не знайдений.")
    except Exception as e:
        logger.error(f"Error in enter_hero_name for user {message.from_user.id}: {e}")
        await message.answer("❌ Помилка при обробці імені героя. Спробуйте ще раз.")


@hero_router.callback_query(F.data == "confirm_hero")
async def confirm_hero_creation(callback: CallbackQuery, state: FSMContext):
    """Confirm hero creation."""
    data = await state.get_data()
    class_id = data.get('selected_class_id')
    hero_name = data.get('hero_name')
    
    if not class_id or not hero_name:
        await callback.answer("❌ Помилка: дані не знайдені.")
        return
    
    async for session in get_db_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Користувач не знайдений.")
            return
        
        try:
            # Create hero
            hero = await create_hero(
                session=session,
                user_id=user.id,
                hero_class_id=class_id,
                name=hero_name
            )
            
            # Get hero class for stats display
            hero_class = await get_hero_class_by_id(session, class_id)
            if hero_class:
                hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
                stats_text = HeroCalculator.format_stats_display(hero_stats, hero_class)
                
                # Create keyboard with "Start Journey" button
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🗺️ Розпочати подорож", callback_data="start_journey")]
                ])
                
                try:
                    await callback.message.edit_text(
                        f"🎉 <b>Герой успішно створений!</b>\n\n{stats_text}",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.warning(f"Could not edit message, sending new one: {e}")
                    await callback.message.answer(
                        f"🎉 <b>Герой успішно створений!</b>\n\n{stats_text}",
                        reply_markup=keyboard
                    )
            else:
                # Create keyboard with "Start Journey" button
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🗺️ Розпочати подорож", callback_data="start_journey")]
                ])
                
                try:
                    await callback.message.edit_text(
                        f"🎉 Герой <b>{hero_name}</b> успішно створений!",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.warning(f"Could not edit message, sending new one: {e}")
                    await callback.message.answer(
                        f"🎉 Герой <b>{hero_name}</b> успішно створений!",
                        reply_markup=keyboard
                    )
            
            await state.clear()
            logger.info(f"Hero creation completed for user {callback.from_user.id}, state cleared")
            await callback.answer("✅ Герой створений!")
            
        except Exception as e:
            logger.error(f"Error creating hero: {e}")
            await callback.message.edit_text("❌ Помилка при створенні героя. Спробуйте ще раз.")
            await callback.answer("❌ Помилка створення")


@hero_router.callback_query(F.data == "cancel_hero")
async def cancel_hero_creation(callback: CallbackQuery, state: FSMContext):
    """Cancel hero creation."""
    await state.clear()
    logger.info(f"Hero creation cancelled for user {callback.from_user.id}, state cleared")
    await callback.message.edit_text("❌ Створення героя скасовано.")
    await callback.answer("Скасовано")


@hero_router.callback_query(F.data == "start_journey")
async def start_journey(callback: CallbackQuery, state: FSMContext):
    """Start hero's journey by entering the starting village."""
    user = callback.from_user
    
    # For now, we'll use town_id = 1 as the starting village
    town_id = 1
    
    async for session in get_db_session():
        # Get or create user town progress
        from database import get_user_town_progress, create_user_town_progress, get_town_by_id, get_town_node_by_id
        
        town_progress = await get_user_town_progress(session, user.id, town_id)
        
        if not town_progress:
            # First time visiting - start at town center (node_id = 1)
            town_progress = await create_user_town_progress(
                session=session,
                user_id=user.id,
                town_id=town_id,
                current_node_id=1
            )
            logger.info(f"Created town progress for user {user.id}")
        
        # Get town info
        town = await get_town_by_id(session, town_id)
        if not town:
            await callback.message.edit_text("❌ Місто не знайдено. Зверніться до адміністратора.")
            await callback.answer("❌ Помилка")
            return
        
        # Get current node
        current_node = await get_town_node_by_id(session, town_progress.current_node_id)
        if not current_node:
            await callback.message.edit_text("❌ Поточне місце не знайдено. Зверніться до адміністратора.")
            await callback.answer("❌ Помилка")
            return
        
        # Send welcome message
        from aiogram.utils.markdown import hbold
        welcome_text = (
            f"🗺️ {hbold('Подорож розпочата!')}\n\n"
            f"🏘️ {hbold('Ласкаво просимо до')} {hbold(town.name)}!\n\n"
            f"{town.description}\n\n"
            f"📍 {hbold('Поточне місце:')} {current_node.name}\n"
            f"{current_node.description}\n\n"
            f"Оберіть наступну дію:"
        )
        
        # Get available connections
        from database import get_town_connections
        connections = await get_town_connections(session, current_node.id)
        
        # Create keyboard with available actions
        from keyboards import create_town_keyboard
        keyboard = await create_town_keyboard(connections, current_node.id)
        
        try:
            await callback.message.edit_text(welcome_text, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Could not edit message, sending new one: {e}")
            await callback.message.answer(welcome_text, reply_markup=keyboard)
        
        await callback.answer("🗺️ Подорож розпочата!")
        logger.info(f"User {user.id} started journey to town {town_id}")
        
        # Clear FSM state after starting journey
        await state.clear()
        logger.info(f"FSM state cleared for user {user.id} after starting journey")


@hero_router.message(Command("classes"))
async def show_classes_command(message: Message):
    """Show all available hero classes."""
    async for session in get_db_session():
        hero_classes = await get_all_hero_classes(session)
        
        if not hero_classes:
            await message.answer("❌ Немає доступних класів героїв.")
            return
        
        classes_text = "⚔️ <b>Доступні класи героїв:</b>\n\n"
        
        for hero_class in hero_classes:
            class_info = HeroCalculator.format_class_info(hero_class)
            classes_text += f"{class_info}\n\n"
        
        await message.answer(classes_text)


@hero_router.message(Command("stats"))
async def show_stats_command(message: Message):
    """Show hero stats (alias for /hero)."""
    await hero_command(message, None)


# Admin commands for managing hero classes
@hero_router.message(Command("init_classes"))
async def init_hero_classes_command(message: Message):
    """Initialize default hero classes (admin command)."""
    # Check if user is admin (you can implement proper admin check)
    if message.from_user.id not in [123456789]:  # Replace with actual admin IDs
        await message.answer("❌ Доступ заборонено.")
        return
    
    async for session in get_db_session():
        try:
            # Check if classes already exist
            existing_classes = await get_all_hero_classes(session)
            if existing_classes:
                await message.answer("⚠️ Класи героїв вже ініціалізовані.")
                return
            
            # Create all hero classes
            classes_data = HeroClasses.get_all_classes()
            created_classes = []
            
            for class_data in classes_data:
                hero_class = await create_hero_class(
                    session=session,
                    name=class_data['name'],
                    description=class_data['description'],
                    str_bonus=class_data['str_bonus'],
                    agi_bonus=class_data['agi_bonus'],
                    int_bonus=class_data['int_bonus'],
                    vit_bonus=class_data['vit_bonus'],
                    luk_bonus=class_data['luk_bonus'],
                    stat_growth=class_data['stat_growth']
                )
                created_classes.append(hero_class.name)
            
            await message.answer(
                f"✅ Класи героїв успішно ініціалізовані:\n"
                f"• {', '.join(created_classes)}"
            )
            
        except Exception as e:
            logger.error(f"Error initializing hero classes: {e}")
            await message.answer("❌ Помилка при ініціалізації класів героїв.")


@hero_router.callback_query(F.data.startswith("hero_menu_from_inn:"))
async def hero_menu_from_inn_handler(callback: CallbackQuery):
    """Handle hero menu button from inn."""
    await callback.answer()
    
    # Parse callback data to get town_id and node_id
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    async for session in get_db_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("❌ Користувач не знайдений. Використайте /start для реєстрації.")
            return
        
        hero = await get_hero_by_user_id(session, user.id)
        
        if hero:
            # Show existing hero info
            hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
            if hero_class:
                hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
                stats_text = HeroCalculator.format_stats_display(hero_stats, hero_class)
                
                # Create keyboard with close button that returns to inn
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚪 Повернутися в таверну", callback_data=f"close_hero_to_inn:{town_id}:{node_id}")]
                ])
                
                await callback.message.edit_text(stats_text, reply_markup=keyboard)
            else:
                await callback.message.answer("❌ Помилка: клас героя не знайдений.")
        else:
            # No hero exists, offer to create one
            await callback.message.edit_text(
                "👤 У вас ще немає героя!\n\n"
                "Створіть свого героя, щоб почати пригоди:\n"
                "• Виберіть клас героя\n"
                "• Дайте йому ім'я\n"
                "• Почніть свою подорож!\n\n"
                "Використайте /create_hero для створення героя.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚪 Повернутися в таверну", callback_data=f"close_hero_to_inn:{town_id}:{node_id}")]
                ])
            )


@hero_router.callback_query(F.data == "hero_menu")
async def hero_menu_handler(callback: CallbackQuery):
    """Handle hero menu button from other locations (fallback)."""
    await callback.answer()
    
    async for session in get_db_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("❌ Користувач не знайдений. Використайте /start для реєстрації.")
            return
        
        hero = await get_hero_by_user_id(session, user.id)
        
        if hero:
            # Show existing hero info
            hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
            if hero_class:
                hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
                stats_text = HeroCalculator.format_stats_display(hero_stats, hero_class)
                
                # Create keyboard with close button
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚪 Закрити", callback_data="close_hero_info")]
                ])
                
                await callback.message.edit_text(stats_text, reply_markup=keyboard)
            else:
                await callback.message.answer("❌ Помилка: клас героя не знайдений.")
        else:
            # No hero exists, offer to create one
            await callback.message.edit_text(
                "👤 У вас ще немає героя!\n\n"
                "Створіть свого героя, щоб почати пригоди:\n"
                "• Виберіть клас героя\n"
                "• Дайте йому ім'я\n"
                "• Почніть свою подорож!\n\n"
                "Використайте /create_hero для створення героя.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚪 Закрити", callback_data="close_hero_info")]
                ])
            )


@hero_router.callback_query(F.data.startswith("close_hero_to_inn:"))
async def close_hero_to_inn_handler(callback: CallbackQuery):
    """Handle close hero info and return to inn."""
    await callback.answer()
    
    # Parse callback data to get town_id and node_id
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    # Import here to avoid circular imports
    from town_handlers import handle_town_back_to_location
    
    # Create a mock callback with the correct data for town_back_to_location
    class MockCallback:
        def __init__(self, original_callback, town_id, node_id):
            self.message = original_callback.message
            self.from_user = original_callback.from_user
            self.data = f"town_back_to_location:{town_id}:{node_id}"
            self.answer = original_callback.answer
    
    mock_callback = MockCallback(callback, town_id, node_id)
    await handle_town_back_to_location(mock_callback)


@hero_router.callback_query(F.data == "close_hero_info")
async def close_hero_info(callback: CallbackQuery):
    """Handle close hero info button."""
    await callback.message.delete()
    await callback.answer("📋 Інформація про героя закрита")


def register_hero_handlers(dp):
    """Register hero handlers with the dispatcher."""
    dp.include_router(hero_router)
