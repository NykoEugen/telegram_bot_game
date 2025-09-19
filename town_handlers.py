"""
Town/Location system handlers for the RPG bot.
"""
import logging
import json
from typing import Optional

from aiogram import Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic

from database import (
    AsyncSessionLocal,
    get_town_by_id,
    get_town_node_by_id,
    get_town_nodes,
    get_town_connections,
    get_town_connections_bidirectional,
    create_user_town_progress,
    get_user_town_progress,
    update_user_town_progress
)
from keyboards import TownKeyboardBuilder

logger = logging.getLogger(__name__)

# Create router for town handlers
router = Router()


async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None):
    """Safely edit a message, handling 'message not modified' errors."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" in str(e):
            # Message is the same, just answer the callback
            await callback.answer("No changes needed!")
        else:
            # Other error, re-raise
            raise


@router.message(Command("town"))
async def cmd_town(message: Message):
    """Handle /town command to enter the starting village."""
    user = message.from_user
    
    # For now, we'll use town_id = 1 as the starting village
    town_id = 1
    
    async with AsyncSessionLocal() as session:
        # Get or create user town progress
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
            await message.answer("❌ Town not found. Please contact administrator.")
            return
        
        # Get current node
        current_node = await get_town_node_by_id(session, town_progress.current_node_id)
        if not current_node:
            await message.answer("❌ Current location not found. Please contact administrator.")
            return
        
        # Send welcome message
        welcome_text = (
            f"🏘️ {hbold('Welcome to')} {hbold(town.name)}!\n\n"
            f"{town.description}\n\n"
            f"📍 {hbold('Current Location:')} {current_node.name}\n"
            f"{current_node.description}\n\n"
            f"Choose your next action:"
        )
        
        # Get available connections
        connections = await get_town_connections(session, current_node.id)
        
        # Create appropriate keyboard based on node type
        if current_node.node_type == "guild":
            keyboard = TownKeyboardBuilder.guild_keyboard(town_id, current_node.id)
        elif current_node.node_type == "barracks":
            keyboard = TownKeyboardBuilder.barracks_keyboard(town_id, current_node.id)
        elif current_node.node_type == "square":
            keyboard = TownKeyboardBuilder.square_keyboard(town_id, current_node.id)
        elif current_node.node_type == "inn":
            keyboard = TownKeyboardBuilder.inn_keyboard(town_id, current_node.id)
        else:
            keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, current_node.id, connections)
        
        await message.answer(welcome_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("town_explore:"))
async def handle_town_explore(callback: CallbackQuery):
    """Handle town exploration."""
    await callback.answer()
    
    town_id = int(callback.data.split(":")[1])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Get town progress
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if not town_progress:
            await callback.message.answer("❌ Town progress not found. Use /town to start.")
            return
        
        # Get current node
        current_node = await get_town_node_by_id(session, town_progress.current_node_id)
        if not current_node:
            await callback.message.answer("❌ Current location not found.")
            return
        
        # Get available connections
        connections = await get_town_connections(session, current_node.id)
        
        # Create navigation keyboard
        keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, current_node.id, connections)
        
        explore_text = (
            f"🔍 {hbold('Exploring')} {current_node.name}\n\n"
            f"{current_node.description}\n\n"
            f"Available paths:"
        )
        
        await safe_edit_message(callback, explore_text, keyboard)


@router.callback_query(F.data.startswith("town_map:"))
async def handle_town_map(callback: CallbackQuery):
    """Handle town map display."""
    await callback.answer()
    
    town_id = int(callback.data.split(":")[1])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Get town info
        town = await get_town_by_id(session, town_id)
        if not town:
            await callback.message.answer("❌ Town not found.")
            return
        
        # Get all town nodes
        nodes = await get_town_nodes(session, town_id)
        
        # Create map keyboard
        keyboard = TownKeyboardBuilder.town_map_keyboard(town_id, nodes)
        
        map_text = (
            f"🗺️ {hbold('Town Map')} - {town.name}\n\n"
            f"Available locations:\n"
        )
        
        # Add node descriptions
        for node in nodes:
            if node.is_accessible:
                emoji_map = {
                    'guild': '🏴‍☠️',
                    'barracks': '🏰',
                    'square': '🏛️',
                    'inn': '🏨',
                    'shop': '🏪',
                    'temple': '⛪',
                    'default': '📍'
                }
                emoji = emoji_map.get(node.node_type, '📍')
                map_text += f"{emoji} {node.name}\n"
        
        await safe_edit_message(callback, map_text, keyboard)


@router.callback_query(F.data.startswith("town_info:"))
async def handle_town_info(callback: CallbackQuery):
    """Handle town information display."""
    await callback.answer()
    
    town_id = int(callback.data.split(":")[1])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Get town info
        town = await get_town_by_id(session, town_id)
        if not town:
            await callback.message.answer("❌ Town not found.")
            return
        
        # Get town progress
        town_progress = await get_user_town_progress(session, user.id, town_id)
        
        # Get all town nodes
        nodes = await get_town_nodes(session, town_id)
        
        info_text = (
            f"ℹ️ {hbold('Town Information')}\n\n"
            f"🏘️ {hbold('Name:')} {town.name}\n"
            f"🏷️ {hbold('Type:')} {town.town_type.title()}\n"
            f"📝 {hbold('Description:')} {town.description}\n\n"
            f"📍 {hbold('Locations:')} {len(nodes)}\n"
        )
        
        if town_progress:
            visited_nodes = json.loads(town_progress.visited_nodes or "[]")
            info_text += f"✅ {hbold('Visited:')} {len(visited_nodes)}/{len(nodes)}\n"
            info_text += f"🕐 {hbold('Last Visit:')} {town_progress.last_visited_at}\n"
        
        # Create back button
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔙 Back to Town",
            callback_data=f"town_explore:{town_id}"
        )
        keyboard = builder.as_markup()
        
        await safe_edit_message(callback, info_text, keyboard)


@router.callback_query(F.data.startswith("town_move:"))
async def handle_town_move(callback: CallbackQuery):
    """Handle movement between town nodes."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    from_node_id = int(parts[2])
    to_node_id = int(parts[3])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Verify connection exists
        connections = await get_town_connections(session, from_node_id)
        valid_connection = any(conn.to_node_id == to_node_id for conn in connections)
        
        if not valid_connection:
            await callback.message.answer("❌ You cannot go there from here.")
            return
        
        # Get target node
        target_node = await get_town_node_by_id(session, to_node_id)
        if not target_node:
            await callback.message.answer("❌ Target location not found.")
            return
        
        # Update user progress
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if town_progress:
            await update_user_town_progress(
                session=session,
                progress=town_progress,
                current_node_id=to_node_id
            )
        
        # Send arrival message
        arrival_text = (
            f"🚶 {hbold('You arrive at')} {target_node.name}\n\n"
            f"{target_node.description}\n\n"
            f"What would you like to do?"
        )
        
        # Get available connections from new location
        new_connections = await get_town_connections(session, to_node_id)
        
        # Create appropriate keyboard based on node type
        if target_node.node_type == "guild":
            keyboard = TownKeyboardBuilder.guild_keyboard(town_id, target_node.id)
        elif target_node.node_type == "barracks":
            keyboard = TownKeyboardBuilder.barracks_keyboard(town_id, target_node.id)
        elif target_node.node_type == "square":
            keyboard = TownKeyboardBuilder.square_keyboard(town_id, target_node.id)
        elif target_node.node_type == "inn":
            keyboard = TownKeyboardBuilder.inn_keyboard(town_id, target_node.id)
        else:
            keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, target_node.id, new_connections)
        
        await safe_edit_message(callback, arrival_text, keyboard)


@router.callback_query(F.data.startswith("town_go_to:"))
async def handle_town_go_to(callback: CallbackQuery):
    """Handle direct navigation to a town node from map."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Get target node
        target_node = await get_town_node_by_id(session, node_id)
        if not target_node:
            await callback.message.answer("❌ Target location not found.")
            return
        
        # Update user progress
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if town_progress:
            await update_user_town_progress(
                session=session,
                progress=town_progress,
                current_node_id=node_id
            )
        
        # Send arrival message
        arrival_text = (
            f"🚶 {hbold('You arrive at')} {target_node.name}\n\n"
            f"{target_node.description}\n\n"
            f"What would you like to do?"
        )
        
        # Get available connections from new location
        connections = await get_town_connections(session, node_id)
        
        # Create appropriate keyboard based on node type
        if target_node.node_type == "guild":
            keyboard = TownKeyboardBuilder.guild_keyboard(town_id, target_node.id)
        elif target_node.node_type == "barracks":
            keyboard = TownKeyboardBuilder.barracks_keyboard(town_id, target_node.id)
        elif target_node.node_type == "square":
            keyboard = TownKeyboardBuilder.square_keyboard(town_id, target_node.id)
        elif target_node.node_type == "inn":
            keyboard = TownKeyboardBuilder.inn_keyboard(town_id, target_node.id)
        else:
            keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, target_node.id, connections)
        
        await safe_edit_message(callback, arrival_text, keyboard)


@router.callback_query(F.data.startswith("town_center:"))
async def handle_town_center(callback: CallbackQuery):
    """Handle return to town center."""
    await callback.answer()
    
    town_id = int(callback.data.split(":")[1])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Update user progress to town center (node_id = 1)
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if town_progress:
            await update_user_town_progress(
                session=session,
                progress=town_progress,
                current_node_id=1
            )
        
        # Get town center node
        center_node = await get_town_node_by_id(session, 1)
        if not center_node:
            await callback.message.answer("❌ Town center not found.")
            return
        
        # Send center message
        center_text = (
            f"🏠 {hbold('Town Center')}\n\n"
            f"{center_node.description}\n\n"
            f"Where would you like to go?"
        )
        
        # Get available connections from center
        connections = await get_town_connections(session, 1)
        keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, 1, connections)
        
        await safe_edit_message(callback, center_text, keyboard)


# Guild-specific handlers
@router.callback_query(F.data.startswith("guild_quests:"))
async def handle_guild_quests(callback: CallbackQuery):
    """Handle guild quest board."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    # Get available quests from database
    async with AsyncSessionLocal() as session:
        from database import get_active_quests
        quests = await get_active_quests(session)
        
        quest_text = (
            f"📋 {hbold('Thieves Guild Quest Board')}\n\n"
            f"Welcome to the guild, adventurer! Here you can find various quests and contracts.\n\n"
            f"🔍 {hbold('Available Quests:')}\n"
        )
        
        # Add quests from database
        for quest in quests[:3]:  # Show first 3 quests
            quest_text += f"• {quest.title} - {quest.description[:50]}...\n"
        
        quest_text += f"\nUse /quests to see all available quests in the system."
    
    # Create keyboard with quest options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    # Add buttons for each quest
    for quest in quests[:3]:
        builder.button(
            text=f"🎯 {quest.title}",
            callback_data=f"quest_start:{quest.id}"
        )
    
    # Add back button
    builder.button(
        text="🔙 Back to Guild",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    
    # Add view all quests button
    builder.button(
        text="📋 All Quests",
        callback_data="quest_list"
    )
    
    builder.adjust(1, 2)
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, quest_text, keyboard)


@router.callback_query(F.data.startswith("guild_talk:"))
async def handle_guild_talk(callback: CallbackQuery):
    """Handle talking to guild members."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    talk_text = (
        f"🗣️ {hbold('Talking to Guild Members')}\n\n"
        f"You approach a group of seasoned adventurers sitting around a table.\n\n"
        f"\"Hey there, newcomer!\" says a grizzled rogue. \"Heard you're looking for work?\"\n\n"
        f"\"The city guard has been getting more active lately,\" adds another. \"Might be some good opportunities for someone with your skills.\"\n\n"
        f"\"Just remember,\" warns a third, \"we don't ask questions about your past, and you don't ask about ours.\""
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Guild",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, talk_text, keyboard)


@router.callback_query(F.data.startswith("guild_services:"))
async def handle_guild_services(callback: CallbackQuery):
    """Handle guild services."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    services_text = (
        f"⚔️ {hbold('Guild Services')}\n\n"
        f"The guild offers various services to its members:\n\n"
        f"🔧 {hbold('Equipment:')}\n"
        f"• Lockpicks and tools\n"
        f"• Disguises and costumes\n"
        f"• Information about targets\n\n"
        f"💰 {hbold('Services:')}\n"
        f"• Fence stolen goods\n"
        f"• Provide safe houses\n"
        f"• Arrange meetings with contacts\n\n"
        f"\"Come back when you have some gold to spend,\" says the guild master."
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Guild",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, services_text, keyboard)


# Barracks-specific handlers
@router.callback_query(F.data.startswith("barracks_monsters:"))
async def handle_barracks_monsters(callback: CallbackQuery):
    """Handle monster hunting board."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    # Get available quests from database
    async with AsyncSessionLocal() as session:
        from database import get_active_quests
        quests = await get_active_quests(session)
        
        monsters_text = (
            f"👹 {hbold('Monster Hunting Board')}\n\n"
            f"The guard captain points to a board covered with wanted posters.\n\n"
            f"🔍 {hbold('Active Bounties:')}\n"
        )
        
        # Add quests from database (filter for combat-related quests)
        combat_quests = [q for q in quests if any(keyword in q.title.lower() for keyword in ['dragon', 'monster', 'beast', 'creature', 'hunt'])]
        for quest in combat_quests[:3]:
            monsters_text += f"• {quest.title} - {quest.description[:50]}...\n"
        
        monsters_text += f"\n\"These creatures threaten our trade routes,\" says the captain. \"We need brave souls to deal with them.\""
    
    # Create keyboard with quest options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    # Add buttons for combat quests
    for quest in combat_quests[:3]:
        builder.button(
            text=f"⚔️ {quest.title}",
            callback_data=f"quest_start:{quest.id}"
        )
    
    # Add back button
    builder.button(
        text="🔙 Back to Barracks",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    
    # Add view all quests button
    builder.button(
        text="📋 All Quests",
        callback_data="quest_list"
    )
    
    builder.adjust(1, 2)
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, monsters_text, keyboard)


@router.callback_query(F.data.startswith("barracks_escort:"))
async def handle_barracks_escort(callback: CallbackQuery):
    """Handle caravan escort missions."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    escort_text = (
        f"🚛 {hbold('Caravan Escort Missions')}\n\n"
        f"A merchant approaches you with a worried expression.\n\n"
        f"\"The roads have become dangerous lately,\" he says. \"I need someone to escort my caravan to the next town.\"\n\n"
        f"🔍 {hbold('Available Escorts:')}\n"
        f"• Merchant caravan to Riverdale (Reward: 100 gold)\n"
        f"• Supply wagon to the mining camp (Reward: 80 gold)\n"
        f"• Noble's carriage to the capital (Reward: 200 gold)\n\n"
        f"\"The journey takes 2-3 days, but the pay is good for those willing to take the risk.\""
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Barracks",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, escort_text, keyboard)


@router.callback_query(F.data.startswith("barracks_guard:"))
async def handle_barracks_guard(callback: CallbackQuery):
    """Handle guard duty missions."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    guard_text = (
        f"🛡️ {hbold('Guard Duty')}\n\n"
        f"The guard sergeant looks you up and down.\n\n"
        f"\"We're always looking for extra hands to help with security,\" he says. \"The work is steady but not glamorous.\"\n\n"
        f"🔍 {hbold('Available Duties:')}\n"
        f"• Night watch at the town gates (Reward: 30 gold)\n"
        f"• Patrol the market district (Reward: 25 gold)\n"
        f"• Guard the town hall during meetings (Reward: 40 gold)\n\n"
        f"\"It's honest work, and we provide equipment. Interested?\""
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Barracks",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, guard_text, keyboard)


# Square-specific handlers
@router.callback_query(F.data.startswith("square_talk:"))
async def handle_square_talk(callback: CallbackQuery):
    """Handle talking to townspeople."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    talk_text = (
        f"🗣️ {hbold('Talking to Townspeople')}\n\n"
        f"You mingle with the crowd in the town square, listening to various conversations.\n\n"
        f"\"Did you hear about the strange lights in the old forest?\" asks a farmer.\n\n"
        f"\"The merchant's guild is offering good prices for rare herbs,\" mentions a trader.\n\n"
        f"\"I saw some suspicious characters near the abandoned temple,\" whispers a concerned citizen.\n\n"
        f"Interesting information! You might want to investigate these rumors."
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Square",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, talk_text, keyboard)


@router.callback_query(F.data.startswith("square_events:"))
async def handle_square_events(callback: CallbackQuery):
    """Handle checking for town events."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    # Get available quests from database
    async with AsyncSessionLocal() as session:
        from database import get_active_quests
        quests = await get_active_quests(session)
        
        events_text = (
            f"📢 {hbold('Town Events')}\n\n"
            f"You check the town notice board for current events and announcements.\n\n"
            f"🔍 {hbold('Current Events:')}\n"
            f"• Weekly market day tomorrow - extra vendors expected\n"
            f"• Town meeting this evening to discuss security\n"
            f"• Traveling merchant arriving next week with exotic goods\n\n"
            f"📋 {hbold('Available Quests:')}\n"
        )
        
        # Add quests from database (filter for general/exploration quests)
        general_quests = [q for q in quests if not any(keyword in q.title.lower() for keyword in ['dragon', 'monster', 'beast', 'creature', 'hunt', 'steal', 'thief'])]
        for quest in general_quests[:3]:
            events_text += f"• {quest.title} - {quest.description[:50]}...\n"
        
        events_text += f"\n📋 {hbold('Announcements:')}\n"
        events_text += f"• Curfew in effect after dark due to recent incidents\n"
        events_text += f"• Reward offered for information about recent thefts\n"
        events_text += f"• New guild members welcome at the Thieves Guild"
    
    # Create keyboard with quest options
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    # Add buttons for general quests
    for quest in general_quests[:3]:
        builder.button(
            text=f"📋 {quest.title}",
            callback_data=f"quest_start:{quest.id}"
        )
    
    # Add back button
    builder.button(
        text="🔙 Back to Square",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    
    # Add view all quests button
    builder.button(
        text="📋 All Quests",
        callback_data="quest_list"
    )
    
    builder.adjust(1, 2)
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, events_text, keyboard)


@router.callback_query(F.data.startswith("square_market:"))
async def handle_square_market(callback: CallbackQuery):
    """Handle market interactions."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    market_text = (
        f"🏪 {hbold('Town Market')}\n\n"
        f"The market square is bustling with activity. Various vendors have set up their stalls.\n\n"
        f"🔍 {hbold('Available Vendors:')}\n"
        f"• Weapons & Armor - \"Best prices in town!\"\n"
        f"• Potions & Herbs - \"Magical remedies for all ailments\"\n"
        f"• General Goods - \"Everything a traveler needs\"\n"
        f"• Food & Drink - \"Fresh bread and ale\"\n\n"
        f"💰 {hbold('Note:')} Trading system not yet implemented. Come back later!"
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Square",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, market_text, keyboard)


# Inn-specific handlers
@router.callback_query(F.data.startswith("inn_rest:"))
async def handle_inn_rest(callback: CallbackQuery):
    """Handle resting at the inn."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    rest_text = (
        f"😴 {hbold('Resting at the Inn')}\n\n"
        f"You rent a room for the night and get a good night's sleep.\n\n"
        f"✨ {hbold('Benefits:')}\n"
        f"• Full health and energy restored\n"
        f"• All status effects cleared\n"
        f"• Save point updated\n\n"
        f"\"Sleep well, traveler,\" says the innkeeper. \"The roads can be dangerous, so rest while you can.\""
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Inn",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, rest_text, keyboard)


@router.callback_query(F.data.startswith("inn_save:"))
async def handle_inn_save(callback: CallbackQuery):
    """Handle saving game at the inn."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    save_text = (
        f"💾 {hbold('Saving Game')}\n\n"
        f"Your progress has been saved at the inn.\n\n"
        f"✅ {hbold('Saved:')}\n"
        f"• Current location and progress\n"
        f"• Quest status and inventory\n"
        f"• Character stats and achievements\n\n"
        f"\"Your belongings are safe with us,\" assures the innkeeper. \"We'll keep everything secure until you return.\""
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Inn",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, save_text, keyboard)


@router.callback_query(F.data.startswith("inn_talk:"))
async def handle_inn_talk(callback: CallbackQuery):
    """Handle talking to the innkeeper."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    
    talk_text = (
        f"🗣️ {hbold('Talking to the Innkeeper')}\n\n"
        f"The friendly innkeeper wipes down the bar and greets you warmly.\n\n"
        f"\"Welcome to the Traveler's Rest!\" he says. \"You look like you've been on the road.\"\n\n"
        f"\"I hear all sorts of stories from travelers like yourself,\" he continues. \"Just yesterday, someone mentioned seeing strange creatures near the old ruins.\"\n\n"
        f"\"If you're looking for work, I'd suggest checking with the guard captain or the guild. They always seem to need help with something.\"\n\n"
        f"\"And if you need a place to stay, our rooms are clean and affordable. Best prices in town!\""
    )
    
    # Create back button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Back to Inn",
        callback_data=f"town_back_to_location:{town_id}:{node_id}"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, talk_text, keyboard)


@router.callback_query(F.data.startswith("town_explore_node:"))
async def handle_town_explore_node(callback: CallbackQuery):
    """Handle exploring a specific town node."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Get current node
        current_node = await get_town_node_by_id(session, node_id)
        if not current_node:
            await callback.message.answer("❌ Current location not found.")
            return
        
        # Get available connections
        connections = await get_town_connections(session, current_node.id)
        
        # Create appropriate keyboard based on node type
        if current_node.node_type == "guild":
            keyboard = TownKeyboardBuilder.guild_keyboard(town_id, current_node.id)
        elif current_node.node_type == "barracks":
            keyboard = TownKeyboardBuilder.barracks_keyboard(town_id, current_node.id)
        elif current_node.node_type == "square":
            keyboard = TownKeyboardBuilder.square_keyboard(town_id, current_node.id)
        elif current_node.node_type == "inn":
            keyboard = TownKeyboardBuilder.inn_keyboard(town_id, current_node.id)
        else:
            keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, current_node.id, connections)
        
        explore_text = (
            f"🔍 {hbold('Exploring')} {current_node.name}\n\n"
            f"{current_node.description}\n\n"
            f"What would you like to do?"
        )
        
        await safe_edit_message(callback, explore_text, keyboard)


@router.callback_query(F.data.startswith("town_leave_building:"))
async def handle_town_leave_building(callback: CallbackQuery):
    """Handle leaving a building and returning to town center."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Update user progress to town center (node_id = 1)
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if town_progress:
            await update_user_town_progress(
                session=session,
                progress=town_progress,
                current_node_id=1
            )
        
        # Get town center node
        center_node = await get_town_node_by_id(session, 1)
        if not center_node:
            await callback.message.answer("❌ Town center not found.")
            return
        
        # Send departure message
        departure_text = (
            f"🚪 {hbold('You leave the building')}\n\n"
            f"🏠 {hbold('Town Center')}\n\n"
            f"{center_node.description}\n\n"
            f"Where would you like to go?"
        )
        
        # Get available connections from center
        connections = await get_town_connections(session, 1)
        keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, 1, connections)
        
        await safe_edit_message(callback, departure_text, keyboard)


@router.callback_query(F.data.startswith("town_back_to_location:"))
async def handle_town_back_to_location(callback: CallbackQuery):
    """Handle going back to the previous location (from dialog to building)."""
    await callback.answer()
    
    parts = callback.data.split(":")
    town_id = int(parts[1])
    node_id = int(parts[2])
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Get the target node (the building we're returning to)
        target_node = await get_town_node_by_id(session, node_id)
        if not target_node:
            await callback.message.answer("❌ Target location not found.")
            return
        
        # Update user progress to the target node
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if town_progress:
            await update_user_town_progress(
                session=session,
                progress=town_progress,
                current_node_id=node_id
            )
        
        # Send return message
        return_text = (
            f"🔙 {hbold('You return to')} {target_node.name}\n\n"
            f"{target_node.description}\n\n"
            f"What would you like to do?"
        )
        
        # Create appropriate keyboard based on node type
        if target_node.node_type == "guild":
            keyboard = TownKeyboardBuilder.guild_keyboard(town_id, target_node.id)
        elif target_node.node_type == "barracks":
            keyboard = TownKeyboardBuilder.barracks_keyboard(town_id, target_node.id)
        elif target_node.node_type == "square":
            keyboard = TownKeyboardBuilder.square_keyboard(town_id, target_node.id)
        elif target_node.node_type == "inn":
            keyboard = TownKeyboardBuilder.inn_keyboard(town_id, target_node.id)
        else:
            # For other node types, get connections and use general keyboard
            connections = await get_town_connections(session, target_node.id)
            keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, target_node.id, connections)
        
        await safe_edit_message(callback, return_text, keyboard)


async def show_quest_rewards(callback: CallbackQuery, quest_title: str, quest_description: str = ""):
    """Show quest completion rewards before returning to town."""
    # Generate random rewards based on quest type
    import random
    
    # Base rewards
    gold_reward = random.randint(50, 200)
    exp_reward = random.randint(100, 500)
    
    # Additional rewards based on quest type
    additional_rewards = []
    if "dragon" in quest_title.lower():
        additional_rewards.append("🐉 Dragon Scale")
        additional_rewards.append("⚔️ Dragon Slayer Badge")
        gold_reward += 100
    elif "mystery" in quest_title.lower():
        additional_rewards.append("🔍 Detective's Badge")
        additional_rewards.append("📜 Ancient Scroll")
    elif "thief" in quest_title.lower() or "steal" in quest_title.lower():
        additional_rewards.append("🗡️ Thief's Blade")
        additional_rewards.append("💎 Stolen Gem")
    
    # Create rewards text
    rewards_text = (
        f"🎉 {hbold('Quest Completed!')}\n\n"
        f"{hbold(quest_title)}\n\n"
        f"{quest_description}\n\n"
        f"🏆 {hbold('Rewards Earned:')}\n"
        f"💰 {gold_reward} Gold\n"
        f"⭐ {exp_reward} Experience Points\n"
    )
    
    # Add additional rewards
    for reward in additional_rewards:
        rewards_text += f"{reward}\n"
    
    rewards_text += f"\n🎊 {hbold('Congratulations on completing this quest!')}"
    
    # Create keyboard with return to town button
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🏘️ Return to Town",
        callback_data="quest_return_to_town"
    )
    keyboard = builder.as_markup()
    
    await safe_edit_message(callback, rewards_text, keyboard)


async def auto_return_to_town(callback: CallbackQuery, town_id: int = 1):
    """Automatically return user to town after quest completion."""
    user = callback.from_user
    
    async with AsyncSessionLocal() as session:
        # Update user progress to town center (node_id = 1)
        town_progress = await get_user_town_progress(session, user.id, town_id)
        if town_progress:
            await update_user_town_progress(
                session=session,
                progress=town_progress,
                current_node_id=1
            )
        
        # Get town center node
        center_node = await get_town_node_by_id(session, 1)
        if not center_node:
            await callback.message.answer("❌ Town center not found.")
            return
        
        # Send return message
        return_text = (
            f"🏘️ {hbold('Welcome back to')} Greenbrook Village!\n\n"
            f"🏠 {hbold('Town Center')}\n\n"
            f"{center_node.description}\n\n"
            f"Where would you like to go next?"
        )
        
        # Get available connections from center
        connections = await get_town_connections(session, 1)
        keyboard = TownKeyboardBuilder.town_node_keyboard(town_id, 1, connections)
        
        await safe_edit_message(callback, return_text, keyboard)


@router.callback_query(F.data == "quest_return_to_town")
async def handle_quest_return_to_town(callback: CallbackQuery):
    """Handle return to town from quest rewards screen."""
    await callback.answer()
    await auto_return_to_town(callback)


def register_town_handlers(dp: Dispatcher):
    """Register all town handlers with the dispatcher."""
    dp.include_router(router)
    logger.info("Town handlers registered successfully")
