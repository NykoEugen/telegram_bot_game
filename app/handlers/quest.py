"""
Quest handlers for the Telegram bot game.
"""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic

from app.database import (
    AsyncSessionLocal,
    get_db_session,
    get_user_by_telegram_id,
    get_quest_by_id,
    get_quest_node_by_id,
    get_quest_start_node,
    get_user_quest_progress,
    create_quest_progress,
    update_quest_progress,
    get_active_quests,
    get_hero_for_telegram,
    get_quest_requirements_map,
)
from app.keyboards import QuestKeyboardBuilder
from app.services.progression import record_progress_messages
from app.core.quest_requirements import (
    batch_check_quest_requirements,
    check_quest_requirements,
)

logger = logging.getLogger(__name__)

# Create router for quest handlers
quest_router = Router()


class QuestManager:
    """Quest management class for handling quest logic."""
    
    @staticmethod
    async def start_quest(user_id: int, quest_id: int) -> Optional[dict]:
        """
        Start a quest for a user.
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID to start
            
        Returns:
            Dictionary with quest info and start node, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Check if user exists
            user = await get_user_by_telegram_id(session, user_id)
            if not user:
                return None
            
            # Get quest
            quest = await get_quest_by_id(session, quest_id)
            if not quest or not quest.is_active:
                return None
            
            # Check if user already has progress on this quest
            existing_progress = await get_user_quest_progress(session, user_id, quest_id)
            if existing_progress and existing_progress.status == 'active':
                # User already has active progress, return current state
                current_node = await get_quest_node_by_id(session, existing_progress.current_node_id)
                return {
                    'quest': quest,
                    'current_node': current_node,
                    'progress': existing_progress
                }

            hero = await get_hero_for_telegram(session, user_id)
            requirement_result = await check_quest_requirements(
                session=session,
                quest_id=quest.id,
                user_id=user_id,
                hero_id=hero.id if hero else None,
            )
            if not requirement_result.met:
                return {
                    'quest': quest,
                    'requirements': requirement_result.requirements,
                    'locked_reasons': requirement_result.missing_reasons,
                }

            # Get start node
            start_node = await get_quest_start_node(session, quest_id)
            if not start_node:
                return None
            
            # Create new progress
            progress = await create_quest_progress(session, user_id, quest_id, start_node.id)
            
            return {
                'quest': quest,
                'current_node': start_node,
                'progress': progress
            }
    
    @staticmethod
    async def process_quest_choice(user_id: int, quest_id: int, node_id: int, choice: str) -> Optional[dict]:
        """
        Process user's quest choice (accept/decline).
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID
            node_id: Current node ID
            choice: 'accept' or 'decline'
            
        Returns:
            Dictionary with updated quest state, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Get user progress
            progress = await get_user_quest_progress(session, user_id, quest_id)
            if not progress or progress.status != 'active':
                return None
            
            # Get current node
            current_node = await get_quest_node_by_id(session, node_id)
            if not current_node:
                return None
            
            if choice == 'accept':
                # Move to next node if available
                if current_node.next_node_id:
                    next_node = await get_quest_node_by_id(session, current_node.next_node_id)
                    if next_node:
                        # Update progress to next node
                        await update_quest_progress(session, progress, current_node_id=next_node.id)
                        
                        # Check if quest is completed
                        if next_node.is_final:
                            await update_quest_progress(session, progress, status='completed')
                        
                        return {
                            'quest': await get_quest_by_id(session, quest_id),
                            'current_node': next_node,
                            'progress': progress,
                            'completed': next_node.is_final
                        }
                    else:
                        # Next node not found, complete quest
                        await update_quest_progress(session, progress, status='completed')
                        return {
                            'quest': await get_quest_by_id(session, quest_id),
                            'current_node': current_node,
                            'progress': progress,
                            'completed': True
                        }
                else:
                    # No next node, complete quest
                    await update_quest_progress(session, progress, status='completed')
                    return {
                        'quest': await get_quest_by_id(session, quest_id),
                        'current_node': current_node,
                        'progress': progress,
                        'completed': True
                    }
            
            elif choice == 'decline':
                # Decline quest
                await update_quest_progress(session, progress, status='declined')
                return {
                    'quest': await get_quest_by_id(session, quest_id),
                    'current_node': current_node,
                    'progress': progress,
                    'declined': True
                }
            
            return None


# Quest command handlers
@quest_router.message(Command("quests"))
async def cmd_quests(message: Message):
    """Show available quests."""
    async with AsyncSessionLocal() as session:
        quests = await get_active_quests(session)
        
        if not quests:
            await message.answer(
                f"{hbold('Available Quests')}\n\n"
                f"No quests are currently available. Check back later!"
            )
            return

        hero = await get_hero_for_telegram(session, message.from_user.id)
        hero_id = hero.id if hero else None

        quest_ids = [quest.id for quest in quests]
        requirements_map = await get_quest_requirements_map(session, quest_ids)
        requirement_results = await batch_check_quest_requirements(
            session=session,
            quest_ids=quest_ids,
            user_id=message.from_user.id,
            hero_id=hero_id,
            requirements_map=requirements_map,
        )

        available: list = []
        locked: list = []
        for quest in quests:
            result = requirement_results.get(quest.id)
            if not result or result.met:
                available.append(quest)
            else:
                locked.append((quest, result))

        quest_text = f"{hbold('Available Quests')}\n\n"

        if available:
            for quest in available:
                quest_text += f"🎯 {hbold(quest.title)}\n{quest.description}\n\n"
        else:
            quest_text += "Наразі немає квестів, які ви можете розпочати.\n\n"

        if locked:
            quest_text += f"{hbold('🔒 Недоступні квести')}\n\n"
            for quest, result in locked:
                quest_text += f"🚫 {hbold(quest.title)}\n"
                for reason in result.missing_reasons:
                    quest_text += f"- {reason}\n"
                quest_text += "\n"

        from app.keyboards import GraphQuestKeyboardBuilder

        keyboard = GraphQuestKeyboardBuilder.graph_quest_list_keyboard([
            {'id': quest.id, 'title': quest.title} for quest in available
        ])

        await message.answer(quest_text, reply_markup=keyboard)


@quest_router.message(Command("quest"))
async def cmd_quest(message: Message):
    """Start a quest (usage: /quest &lt;quest_id&gt;)."""
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{hbold('Quest Command')}\n\n"
            f"Usage: /quest &lt;quest_id&gt;\n"
            f"Use /quests to see available quests."
        )
        return
    
    try:
        quest_id = int(args[1])
    except ValueError:
        await message.answer("Invalid quest ID. Please provide a number.")
        return
    
    user_id = message.from_user.id
    
    # Try to start as graph quest first (for quests with ID >= 2)
    if quest_id >= 1:
        from app.handlers.graph_quest import GraphQuestManager
        from app.keyboards import GraphQuestKeyboardBuilder
        
        quest_data = await GraphQuestManager.start_graph_quest(user_id, quest_id)
        
        if quest_data:
            quest = quest_data['quest']
            if quest_data.get('locked_reasons'):
                reasons = "\n".join(f"- {reason}" for reason in quest_data['locked_reasons'])
                await message.answer(
                    f"{hbold(quest.title)} наразі недоступний.\n\n{reasons}"
                )
                return

            current_node = quest_data['current_node']
            connections = quest_data['connections']
            event_messages = quest_data.get('event_messages') or []

            if quest_data.get('recovery_required'):
                recovery_lines = [
                    f"{hbold('Потрібне відновлення!')}",
                    "Герой занадто виснажений після події. Відновіть здоров'я у місті, щоб продовжити."
                ]
                if event_messages:
                    recovery_lines.append("")
                    recovery_lines.extend(event_messages)
                from app.keyboards import GraphQuestKeyboardBuilder
                await message.answer(
                    "\n".join(recovery_lines),
                    reply_markup=GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(quest.id, current_node.id)
                )
                return

            # Send quest start message
            quest_text = (
                f"{hbold('🎯 Graph Quest Started!')}\n\n"
                f"{hbold(quest.title)}\n\n"
                f"{hbold(current_node.title)}\n"
                f"{current_node.description}\n\n"
                f"What will you do?"
            )

            if event_messages:
                quest_text += "\n\n" + "\n".join(event_messages)
            
            keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
                quest.id, current_node.id, connections
            )
            await message.answer(quest_text, reply_markup=keyboard)
            return
    
    quest_data = await QuestManager.start_quest(user_id, quest_id)

    if not quest_data:
        await message.answer("Quest not found or cannot be started.")
        return

    quest = quest_data['quest']

    if quest_data.get('locked_reasons'):
        reasons = "\n".join(f"- {reason}" for reason in quest_data['locked_reasons'])
        await message.answer(
            f"{hbold(quest.title)} наразі недоступний.\n\n{reasons}"
        )
        return

    current_node = quest_data['current_node']
    event_messages = quest_data.get('event_messages') or []

    quest_text = (
        f"{hbold('🎯 Quest Started!')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{hbold(current_node.title)}\n"
        f"{current_node.description}\n\n"
        f"What will you do?"
    )

    if event_messages:
        quest_text += "\n\n" + "\n".join(event_messages)
    
    keyboard = QuestKeyboardBuilder.quest_choice_keyboard(quest.id, current_node.id)
    await message.answer(quest_text, reply_markup=keyboard)


# Quest callback handlers
@quest_router.callback_query(F.data.startswith("quest_start:"))
async def handle_quest_start(callback: CallbackQuery):
    """Handle quest start callback."""
    quest_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Try to start as graph quest first (for quests with ID >= 2)
    if quest_id >= 1:
        from app.handlers.graph_quest import GraphQuestManager
        from app.keyboards import GraphQuestKeyboardBuilder
        
        quest_data = await GraphQuestManager.start_graph_quest(user_id, quest_id)
        
        if quest_data:
            quest = quest_data['quest']
            if quest_data.get('locked_reasons'):
                reasons = "\n".join(f"- {reason}" for reason in quest_data['locked_reasons'])
                await callback.message.answer(
                    f"{hbold(quest.title)} наразі недоступний.\n\n{reasons}"
                )
                await callback.answer("Quest locked", show_alert=True)
                return
            current_node = quest_data['current_node']
            connections = quest_data['connections']
            event_messages = quest_data.get('event_messages') or []

            if quest_data.get('recovery_required'):
                recovery_lines = [
                    f"{hbold('Потрібне відновлення!')}",
                    "Герой занадто виснажений після події. Відновіть здоров'я у місті, щоб продовжити."
                ]
                if event_messages:
                    recovery_lines.append("")
                    recovery_lines.extend(event_messages)
                keyboard = GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(
                    quest.id,
                    current_node.id
                )
                await callback.message.edit_text(
                    "\n".join(recovery_lines),
                    reply_markup=keyboard
                )
                await callback.answer("Спершу відновіться", show_alert=True)
                return
            
            quest_text = (
                f"{hbold('🎯 Graph Quest Started!')}\n\n"
                f"{hbold(quest.title)}\n\n"
                f"{hbold(current_node.title)}\n"
                f"{current_node.description}\n\n"
                f"What will you do?"
            )

            if event_messages:
                quest_text += "\n\n" + "\n".join(event_messages)
            
            keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
                quest.id, current_node.id, connections
            )
            await callback.message.edit_text(quest_text, reply_markup=keyboard)
            await callback.answer()
            return
    
    # Fall back to regular quest for quest ID 1
    quest_data = await QuestManager.start_quest(user_id, quest_id)
    
    if not quest_data:
        await callback.answer("Quest not found or cannot be started.", show_alert=True)
        return

    quest = quest_data['quest']

    if quest_data.get('locked_reasons'):
        reasons = "\n".join(f"- {reason}" for reason in quest_data['locked_reasons'])
        await callback.message.answer(
            f"{hbold(quest.title)} наразі недоступний.\n\n{reasons}"
        )
        await callback.answer("Quest locked", show_alert=True)
        return

    current_node = quest_data['current_node']
    event_messages = quest_data.get('event_messages') or []

    quest_text = (
        f"{hbold('🎯 Quest Started!')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{hbold(current_node.title)}\n"
        f"{current_node.description}\n\n"
        f"What will you do?"
    )

    if event_messages:
        quest_text += "\n\n" + "\n".join(event_messages)

    keyboard = QuestKeyboardBuilder.quest_choice_keyboard(quest.id, current_node.id)
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@quest_router.callback_query(F.data.startswith("quest_accept:"))
async def handle_quest_accept(callback: CallbackQuery):
    """Handle quest accept callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    user_id = callback.from_user.id
    
    result = await QuestManager.process_quest_choice(user_id, quest_id, node_id, 'accept')
    
    if not result:
        await callback.answer("Invalid quest action.", show_alert=True)
        return
    
    quest = result['quest']
    current_node = result['current_node']
    
    if result.get('completed'):
        # Quest completed - show rewards screen
        # Import here to avoid circular imports
        from app.handlers.town import show_quest_rewards
        hero_id = None
        async for session in get_db_session():
            hero = await get_hero_for_telegram(session, user_id)
            if hero:
                hero_id = hero.id
            break

        if hero_id:
            for message_text in await record_progress_messages(hero_id, 'quests_completed', 1):
                await callback.message.answer(message_text)

        await show_quest_rewards(callback, quest.title, current_node.description)
        return
    else:
        # Continue quest
        quest_text = (
            f"{hbold('✅ Choice Accepted!')}\n\n"
            f"{hbold(quest.title)}\n\n"
            f"{hbold(current_node.title)}\n"
            f"{current_node.description}\n\n"
            f"What will you do next?"
        )
        
        keyboard = QuestKeyboardBuilder.quest_choice_keyboard(quest.id, current_node.id)
    
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer("Choice accepted!")


@quest_router.callback_query(F.data.startswith("quest_decline:"))
async def handle_quest_decline(callback: CallbackQuery):
    """Handle quest decline callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    user_id = callback.from_user.id
    
    result = await QuestManager.process_quest_choice(user_id, quest_id, node_id, 'decline')
    
    if not result:
        await callback.answer("Invalid quest action.", show_alert=True)
        return
    
    quest = result['quest']
    
    quest_text = (
        f"{hbold('❌ Quest Declined')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"You have declined this quest. You can start it again later using /quests."
    )
    
    keyboard = QuestKeyboardBuilder.quest_completion_keyboard(quest.id)
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer("Quest declined.")


@quest_router.callback_query(F.data.startswith("quest_menu:"))
async def handle_quest_menu(callback: CallbackQuery):
    """Handle quest menu callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        quest = await get_quest_by_id(session, quest_id)
        current_node = await get_quest_node_by_id(session, node_id)
        
        if not quest or not current_node:
            await callback.answer("Quest not found.", show_alert=True)
            return
    
    quest_text = (
        f"{hbold('📋 Quest Menu')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"Current: {current_node.title}\n\n"
        f"Choose an option:"
    )
    
    keyboard = QuestKeyboardBuilder.quest_menu_keyboard(quest.id, node_id)
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@quest_router.callback_query(F.data.startswith("quest_continue:"))
async def handle_quest_continue(callback: CallbackQuery):
    """Handle quest continue callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        quest = await get_quest_by_id(session, quest_id)
        current_node = await get_quest_node_by_id(session, node_id)
        
        if not quest or not current_node:
            await callback.answer("Quest not found.", show_alert=True)
            return
    
    quest_text = (
        f"{hbold('▶️ Continue Quest')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{hbold(current_node.title)}\n"
        f"{current_node.description}\n\n"
        f"What will you do?"
    )
    
    keyboard = QuestKeyboardBuilder.quest_choice_keyboard(quest.id, current_node.id)
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@quest_router.callback_query(F.data.startswith("quest_progress:"))
async def handle_quest_progress(callback: CallbackQuery):
    """Handle quest progress callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    user_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        quest = await get_quest_by_id(session, quest_id)
        progress = await get_user_quest_progress(session, user_id, quest_id)
        
        if not quest or not progress:
            await callback.answer("Quest progress not found.", show_alert=True)
            return
        
        current_node = await get_quest_node_by_id(session, progress.current_node_id)
    
    progress_text = (
        f"{hbold('📊 Quest Progress')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"Status: {hbold(progress.status.title())}\n"
        f"Current: {current_node.title if current_node else 'Unknown'}\n"
        f"Started: {progress.started_at}\n"
    )
    
    if progress.completed_at:
        progress_text += f"Completed: {progress.completed_at}\n"
    
    keyboard = QuestKeyboardBuilder.quest_menu_keyboard(quest.id, progress.current_node_id)
    await callback.message.edit_text(progress_text, reply_markup=keyboard)
    await callback.answer()


@quest_router.callback_query(F.data.startswith("quest_info:"))
async def handle_quest_info(callback: CallbackQuery):
    """Handle quest info callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    
    async with AsyncSessionLocal() as session:
        quest = await get_quest_by_id(session, quest_id)
        
        if not quest:
            await callback.answer("Quest not found.", show_alert=True)
            return
    
    info_text = (
        f"{hbold('ℹ️ Quest Information')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{quest.description}\n\n"
        f"Created: {quest.created_at}\n"
        f"Status: {'Active' if quest.is_active else 'Inactive'}"
    )
    
    keyboard = QuestKeyboardBuilder.quest_menu_keyboard(quest.id, 0)
    await callback.message.edit_text(info_text, reply_markup=keyboard)
    await callback.answer()


@quest_router.callback_query(F.data == "quest_list")
async def handle_quest_list(callback: CallbackQuery):
    """Handle quest list callback."""
    async with AsyncSessionLocal() as session:
        quests = await get_active_quests(session)
        
        if not quests:
            await callback.answer("No quests available.", show_alert=True)
            return
        
        quest_list = []
        for quest in quests:
            quest_list.append({
                'id': quest.id,
                'title': quest.title
            })
        
        keyboard = QuestKeyboardBuilder.quest_list_keyboard(quest_list)
        
        quest_text = f"{hbold('Available Quests')}\n\n"
        for quest in quests:
            quest_text += f"🎯 {hbold(quest.title)}\n{quest.description}\n\n"
        
        await callback.message.edit_text(quest_text, reply_markup=keyboard)
        await callback.answer()


@quest_router.callback_query(F.data == "quest_refresh")
async def handle_quest_refresh(callback: CallbackQuery):
    """Handle quest refresh callback."""
    await handle_quest_list(callback)


def register_quest_handlers(dp):
    """Register quest handlers with the dispatcher."""
    dp.include_router(quest_router)
    logger.info("Quest handlers registered successfully")
