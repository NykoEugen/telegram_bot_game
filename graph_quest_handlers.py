"""
Graph Quest handlers for the Telegram bot game.
"""
import logging
import json
from typing import Optional, List, Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic

from database import (
    AsyncSessionLocal,
    get_user_by_telegram_id,
    get_graph_quest_by_id,
    get_graph_quest_node_by_id,
    get_graph_quest_start_node,
    get_graph_quest_connections,
    get_user_graph_quest_progress,
    create_graph_quest_progress,
    update_graph_quest_progress,
    get_active_quests,
    GraphQuestNode,
    GraphQuestConnection,
    GraphQuestProgress
)
from keyboards import GraphQuestKeyboardBuilder

logger = logging.getLogger(__name__)

# Create router for graph quest handlers
graph_quest_router = Router()


class GraphQuestManager:
    """Graph quest management class for handling complex quest logic."""
    
    @staticmethod
    async def start_graph_quest(user_id: int, quest_id: int) -> Optional[dict]:
        """
        Start a graph quest for a user.
        
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
            quest = await get_graph_quest_by_id(session, quest_id)
            if not quest or not quest.is_active:
                return None
            
            # Check if user already has progress on this quest
            existing_progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if existing_progress and existing_progress.status == 'active':
                # User already has active progress, return current state
                current_node = await get_graph_quest_node_by_id(session, existing_progress.current_node_id)
                connections = await get_graph_quest_connections(session, existing_progress.current_node_id)
                return {
                    'quest': quest,
                    'current_node': current_node,
                    'connections': connections,
                    'progress': existing_progress
                }
            
            # Get start node
            start_node = await get_graph_quest_start_node(session, quest_id)
            if not start_node:
                return None
            
            # Get connections from start node
            connections = await get_graph_quest_connections(session, start_node.id)
            
            # Create new progress
            progress = await create_graph_quest_progress(session, user_id, quest_id, start_node.id)
            
            return {
                'quest': quest,
                'current_node': start_node,
                'connections': connections,
                'progress': progress
            }
    
    @staticmethod
    async def process_graph_quest_choice(
        user_id: int, 
        quest_id: int, 
        node_id: int, 
        connection_id: int
    ) -> Optional[dict]:
        """
        Process user's quest choice by following a connection.
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID
            node_id: Current node ID
            connection_id: Connection ID to follow
            
        Returns:
            Dictionary with updated quest state, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Get user progress
            progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if not progress or progress.status != 'active':
                return None
            
            # Get current node
            current_node = await get_graph_quest_node_by_id(session, node_id)
            if not current_node:
                return None
            
            # Get all connections from current node
            connections = await get_graph_quest_connections(session, node_id)
            
            # Find the specific connection
            target_connection = None
            for conn in connections:
                if conn.id == connection_id:
                    target_connection = conn
                    break
            
            if not target_connection:
                return None
            
            # Get the target node
            next_node = await get_graph_quest_node_by_id(session, target_connection.to_node_id)
            if not next_node:
                return None
            
            # Update progress to next node
            await update_graph_quest_progress(session, progress, current_node_id=next_node.id)
            
            # Get connections from next node
            next_connections = await get_graph_quest_connections(session, next_node.id)
            
            # Check if quest is completed
            completed = next_node.is_final
            
            if completed:
                await update_graph_quest_progress(session, progress, status='completed')
            
            return {
                'quest': await get_graph_quest_by_id(session, quest_id),
                'current_node': next_node,
                'connections': next_connections,
                'progress': progress,
                'completed': completed,
                'connection_used': target_connection
            }
    
    @staticmethod
    async def get_quest_map(user_id: int, quest_id: int) -> Optional[dict]:
        """
        Get a visual representation of the quest graph for the user.
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID
            
        Returns:
            Dictionary with quest map data, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Get quest
            quest = await get_graph_quest_by_id(session, quest_id)
            if not quest:
                return None
            
            # Get user progress
            progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if not progress:
                return None
            
            # Get all nodes for the quest
            from database import get_graph_quest_nodes
            nodes = await get_graph_quest_nodes(session, quest_id)
            
            # Get visited nodes
            visited_nodes = json.loads(progress.visited_nodes or "[]")
            
            # Create map data
            map_data = {
                'quest': quest,
                'current_node_id': progress.current_node_id,
                'visited_nodes': visited_nodes,
                'nodes': []
            }
            
            for node in nodes:
                node_info = {
                    'id': node.id,
                    'title': node.title,
                    'type': node.node_type,
                    'is_visited': node.id in visited_nodes,
                    'is_current': node.id == progress.current_node_id,
                    'is_final': node.is_final
                }
                map_data['nodes'].append(node_info)
            
            return map_data


# Graph Quest command handlers
@graph_quest_router.message(Command("graph_quests"))
async def cmd_graph_quests(message: Message):
    """Show available graph quests."""
    async with AsyncSessionLocal() as session:
        quests = await get_active_quests(session)
        
        if not quests:
            await message.answer(
                f"{hbold('Available Graph Quests')}\n\n"
                f"No quests are currently available. Check back later!"
            )
            return
        
        # Filter for graph quests (IDs 2 and above for now)
        graph_quests = [q for q in quests if q.id >= 2]
        
        if not graph_quests:
            await message.answer(
                f"{hbold('Available Graph Quests')}\n\n"
                f"No graph quests are currently available. Check back later!"
            )
            return
        
        quest_list = []
        for quest in graph_quests:
            quest_list.append({
                'id': quest.id,
                'title': quest.title
            })
        
        keyboard = GraphQuestKeyboardBuilder.graph_quest_list_keyboard(quest_list)
        
        quest_text = f"{hbold('Available Graph Quests')}\n\n"
        for quest in graph_quests:
            quest_text += f"🎯 {hbold(quest.title)}\n{quest.description}\n\n"
        
        await message.answer(quest_text, reply_markup=keyboard)


@graph_quest_router.message(Command("graph_quest"))
async def cmd_graph_quest(message: Message):
    """Start a graph quest (usage: /graph_quest <quest_id>)."""
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{hbold('Graph Quest Command')}\n\n"
            f"Usage: /graph_quest <quest_id>\n"
            f"Use /graph_quests to see available graph quests."
        )
        return
    
    try:
        quest_id = int(args[1])
    except ValueError:
        await message.answer("Invalid quest ID. Please provide a number.")
        return
    
    user_id = message.from_user.id
    quest_data = await GraphQuestManager.start_graph_quest(user_id, quest_id)
    
    if not quest_data:
        await message.answer("Graph quest not found or you cannot start this quest.")
        return
    
    quest = quest_data['quest']
    current_node = quest_data['current_node']
    connections = quest_data['connections']
    
    # Send quest start message
    quest_text = (
        f"{hbold('🎯 Graph Quest Started!')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{hbold(current_node.title)}\n"
        f"{current_node.description}\n\n"
        f"What will you do?"
    )
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
        quest.id, current_node.id, connections
    )
    await message.answer(quest_text, reply_markup=keyboard)


@graph_quest_router.message(Command("quest_map"))
async def cmd_quest_map(message: Message):
    """Show quest map for current active quest."""
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{hbold('Quest Map Command')}\n\n"
            f"Usage: /quest_map <quest_id>\n"
            f"Shows your progress through the quest graph."
        )
        return
    
    try:
        quest_id = int(args[1])
    except ValueError:
        await message.answer("Invalid quest ID. Please provide a number.")
        return
    
    user_id = message.from_user.id
    map_data = await GraphQuestManager.get_quest_map(user_id, quest_id)
    
    if not map_data:
        await message.answer("Quest not found or you haven't started this quest.")
        return
    
    quest = map_data['quest']
    current_node_id = map_data['current_node_id']
    visited_nodes = map_data['visited_nodes']
    nodes = map_data['nodes']
    
    # Create map visualization
    map_text = f"{hbold('🗺️ Quest Map')}\n\n"
    map_text += f"{hbold(quest.title)}\n\n"
    
    # Show current location
    current_node = next((n for n in nodes if n['id'] == current_node_id), None)
    if current_node:
        map_text += f"📍 {hbold('Current Location:')} {current_node['title']}\n\n"
    
    # Show visited locations
    visited_count = len(visited_nodes)
    total_nodes = len(nodes)
    map_text += f"📊 Progress: {visited_count}/{total_nodes} locations visited\n\n"
    
    # Show all nodes with status
    map_text += f"{hbold('Locations:')}\n"
    for node in nodes:
        status_icon = "📍" if node['is_current'] else "✅" if node['is_visited'] else "❓"
        type_icon = "🏁" if node['is_final'] else "🚪" if node['type'] == 'start' else "🔍"
        map_text += f"{status_icon} {type_icon} {node['title']}\n"
    
    await message.answer(map_text)


# Graph Quest callback handlers
@graph_quest_router.callback_query(F.data.startswith("graph_quest_start:"))
async def handle_graph_quest_start(callback: CallbackQuery):
    """Handle graph quest start callback."""
    quest_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    quest_data = await GraphQuestManager.start_graph_quest(user_id, quest_id)
    
    if not quest_data:
        await callback.answer("Graph quest not found or cannot be started.", show_alert=True)
        return
    
    quest = quest_data['quest']
    current_node = quest_data['current_node']
    connections = quest_data['connections']
    
    quest_text = (
        f"{hbold('🎯 Graph Quest Started!')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{hbold(current_node.title)}\n"
        f"{current_node.description}\n\n"
        f"What will you do?"
    )
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
        quest.id, current_node.id, connections
    )
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@graph_quest_router.callback_query(F.data.startswith("graph_quest_choice:"))
async def handle_graph_quest_choice(callback: CallbackQuery):
    """Handle graph quest choice callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    connection_id = int(parts[3])
    user_id = callback.from_user.id
    
    result = await GraphQuestManager.process_graph_quest_choice(
        user_id, quest_id, node_id, connection_id
    )
    
    if not result:
        await callback.answer("Invalid quest action.", show_alert=True)
        return
    
    quest = result['quest']
    current_node = result['current_node']
    connections = result['connections']
    connection_used = result['connection_used']
    
    if result.get('completed'):
        # Quest completed
        quest_text = (
            f"{hbold('🎉 Quest Completed!')}\n\n"
            f"{hbold(quest.title)}\n\n"
            f"{hbold(current_node.title)}\n"
            f"{current_node.description}\n\n"
            f"Congratulations! You have completed this quest."
        )
        
        keyboard = GraphQuestKeyboardBuilder.graph_quest_completion_keyboard(quest.id)
    else:
        # Continue quest
        quest_text = (
            f"{hbold('✅ Choice Made!')}\n\n"
            f"{hbold(quest.title)}\n\n"
            f"{hbold(current_node.title)}\n"
            f"{current_node.description}\n\n"
            f"What will you do next?"
        )
        
        keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
            quest.id, current_node.id, connections
        )
    
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer(f"Chose: {connection_used.choice_text or 'Continue'}")


@graph_quest_router.callback_query(F.data.startswith("graph_quest_map:"))
async def handle_graph_quest_map(callback: CallbackQuery):
    """Handle graph quest map callback."""
    quest_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    map_data = await GraphQuestManager.get_quest_map(user_id, quest_id)
    
    if not map_data:
        await callback.answer("Quest not found or you haven't started this quest.", show_alert=True)
        return
    
    quest = map_data['quest']
    current_node_id = map_data['current_node_id']
    visited_nodes = map_data['visited_nodes']
    nodes = map_data['nodes']
    
    # Create map visualization
    map_text = f"{hbold('🗺️ Quest Map')}\n\n"
    map_text += f"{hbold(quest.title)}\n\n"
    
    # Show current location
    current_node = next((n for n in nodes if n['id'] == current_node_id), None)
    if current_node:
        map_text += f"📍 {hbold('Current Location:')} {current_node['title']}\n\n"
    
    # Show visited locations
    visited_count = len(visited_nodes)
    total_nodes = len(nodes)
    map_text += f"📊 Progress: {visited_count}/{total_nodes} locations visited\n\n"
    
    # Show all nodes with status
    map_text += f"{hbold('Locations:')}\n"
    for node in nodes:
        status_icon = "📍" if node['is_current'] else "✅" if node['is_visited'] else "❓"
        type_icon = "🏁" if node['is_final'] else "🚪" if node['type'] == 'start' else "🔍"
        map_text += f"{status_icon} {type_icon} {node['title']}\n"
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(quest.id, current_node_id)
    await callback.message.edit_text(map_text, reply_markup=keyboard)
    await callback.answer()


@graph_quest_router.callback_query(F.data.startswith("graph_quest_menu:"))
async def handle_graph_quest_menu(callback: CallbackQuery):
    """Handle graph quest menu callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        quest = await get_graph_quest_by_id(session, quest_id)
        current_node = await get_graph_quest_node_by_id(session, node_id)
        
        if not quest or not current_node:
            await callback.answer("Quest not found.", show_alert=True)
            return
    
    quest_text = (
        f"{hbold('📋 Graph Quest Menu')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"Current: {current_node.title}\n\n"
        f"Choose an option:"
    )
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(quest.id, node_id)
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@graph_quest_router.callback_query(F.data.startswith("graph_quest_continue:"))
async def handle_graph_quest_continue(callback: CallbackQuery):
    """Handle graph quest continue callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        quest = await get_graph_quest_by_id(session, quest_id)
        current_node = await get_graph_quest_node_by_id(session, node_id)
        connections = await get_graph_quest_connections(session, node_id)
        
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
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
        quest.id, current_node.id, connections
    )
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


def register_graph_quest_handlers(dp):
    """Register graph quest handlers with the dispatcher."""
    dp.include_router(graph_quest_router)
    logger.info("Graph quest handlers registered successfully")
