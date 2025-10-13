"""
Custom inline keyboard builder for quest system.
"""
from typing import Dict, List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class QuestKeyboardBuilder:
    """Custom keyboard builder for quest interactions."""
    
    @staticmethod
    def quest_choice_keyboard(quest_id: int, node_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard with Accept, Decline, and Menu buttons for quest choices.
        
        Args:
            quest_id: ID of the quest
            node_id: ID of the current quest node
            
        Returns:
            InlineKeyboardMarkup with quest choice buttons
        """
        builder = InlineKeyboardBuilder()
        
        # Accept button
        builder.button(
            text="✅ Accept",
            callback_data=f"quest_accept:{quest_id}:{node_id}"
        )
        
        # Decline button
        builder.button(
            text="❌ Decline", 
            callback_data=f"quest_decline:{quest_id}:{node_id}"
        )
        
        # Menu button
        builder.button(
            text="📋 Menu",
            callback_data=f"quest_menu:{quest_id}:{node_id}"
        )
        
        # Adjust layout to 2 buttons per row
        builder.adjust(2, 1)
        
        return builder.as_markup()
    
    @staticmethod
    def quest_menu_keyboard(quest_id: int, node_id: int) -> InlineKeyboardMarkup:
        """
        Create quest menu keyboard with various options.
        
        Args:
            quest_id: ID of the quest
            node_id: ID of the current quest node
            
        Returns:
            InlineKeyboardMarkup with menu options
        """
        builder = InlineKeyboardBuilder()
        
        # Continue quest button
        builder.button(
            text="▶️ Continue Quest",
            callback_data=f"quest_continue:{quest_id}:{node_id}"
        )
        
        # Quest progress button
        builder.button(
            text="📊 Progress",
            callback_data=f"quest_progress:{quest_id}:{node_id}"
        )
        
        # Quest info button
        builder.button(
            text="ℹ️ Quest Info",
            callback_data=f"quest_info:{quest_id}:{node_id}"
        )
        
        # Back to choice button
        builder.button(
            text="🔙 Back to Choice",
            callback_data=f"quest_choice:{quest_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 2)
        
        return builder.as_markup()
    
    @staticmethod
    def quest_list_keyboard(quests: List[dict]) -> InlineKeyboardMarkup:
        """
        Create keyboard for listing available quests.
        
        Args:
            quests: List of quest dictionaries with 'id' and 'title' keys
            
        Returns:
            InlineKeyboardMarkup with quest list buttons
        """
        builder = InlineKeyboardBuilder()
        
        for quest in quests:
            builder.button(
                text=f"🎯 {quest['title']}",
                callback_data=f"quest_start:{quest['id']}"
            )
        
        # Add refresh button
        builder.button(
            text="🔄 Refresh",
            callback_data="quest_refresh"
        )
        
        # Adjust layout to 1 button per row
        builder.adjust(1)
        
        return builder.as_markup()
    
    @staticmethod
    def quest_navigation_keyboard(quest_id: int, node_id: int, has_next: bool = True) -> InlineKeyboardMarkup:
        """
        Create navigation keyboard for quest progression.
        
        Args:
            quest_id: ID of the quest
            node_id: ID of the current quest node
            has_next: Whether there's a next node available
            
        Returns:
            InlineKeyboardMarkup with navigation buttons
        """
        builder = InlineKeyboardBuilder()
        
        if has_next:
            # Next button
            builder.button(
                text="➡️ Next",
                callback_data=f"quest_next:{quest_id}:{node_id}"
            )
        
        # Menu button
        builder.button(
            text="📋 Menu",
            callback_data=f"quest_menu:{quest_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(1)
        
        return builder.as_markup()
    
    @staticmethod
    def quest_completion_keyboard(quest_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for quest completion.
        
        Args:
            quest_id: ID of the completed quest
            
        Returns:
            InlineKeyboardMarkup with completion options
        """
        builder = InlineKeyboardBuilder()
        
        # View other quests button
        builder.button(
            text="🎯 Other Quests",
            callback_data="quest_list"
        )
        
        # Quest stats button
        builder.button(
            text="📊 My Stats",
            callback_data="quest_stats"
        )
        
        # Adjust layout
        builder.adjust(1)
        
        return builder.as_markup()


class GraphQuestKeyboardBuilder:
    """Custom keyboard builder for graph quest interactions."""
    
    @staticmethod
    def graph_quest_choice_keyboard(
        quest_id: int, 
        node_id: int, 
        connections: List[object]
    ) -> InlineKeyboardMarkup:
        """
        Create keyboard with multiple choice options for graph quests.
        
        Args:
            quest_id: ID of the quest
            node_id: ID of the current quest node
            connections: List of GraphQuestConnection objects
            
        Returns:
            InlineKeyboardMarkup with choice buttons
        """
        builder = InlineKeyboardBuilder()
        
        # Add choice buttons for each connection
        for connection in connections:
            if connection.connection_type == 'choice' and connection.choice_text:
                builder.button(
                    text=f"🔹 {connection.choice_text}",
                    callback_data=f"graph_quest_choice:{quest_id}:{node_id}:{connection.id}"
                )
            elif connection.connection_type == 'default':
                builder.button(
                    text="➡️ Continue",
                    callback_data=f"graph_quest_choice:{quest_id}:{node_id}:{connection.id}"
                )
        
        # Add menu button
        builder.button(
            text="📋 Menu",
            callback_data=f"graph_quest_menu:{quest_id}:{node_id}"
        )
        
        # Adjust layout to 1 button per row for choices, menu on separate row
        if connections:
            builder.adjust(len(connections), 1)
        else:
            builder.adjust(1)
        
        return builder.as_markup()

    @staticmethod
    def graph_quest_menu_keyboard(quest_id: int, node_id: int) -> InlineKeyboardMarkup:
        """Create graph quest menu keyboard with various options."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text="▶️ Continue Quest",
            callback_data=f"graph_quest_continue:{quest_id}:{node_id}"
        )
        builder.button(
            text="🗺️ Quest Map",
            callback_data=f"graph_quest_map:{quest_id}"
        )
        builder.button(
            text="📊 Progress",
            callback_data=f"graph_quest_progress:{quest_id}:{node_id}"
        )
        builder.button(
            text="ℹ️ Quest Info",
            callback_data=f"graph_quest_info:{quest_id}:{node_id}"
        )

        builder.adjust(2, 2)
        return builder.as_markup()

    @staticmethod
    def encounter_keyboard(quest_id: int, node_id: int, encounter) -> InlineKeyboardMarkup:
        """Create keyboard for encounter options."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text="⚔️ Fight",
            callback_data=f"encounter_combat:{quest_id}:{node_id}"
        )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def graph_quest_list_keyboard(quests: List[dict]) -> InlineKeyboardMarkup:
        """Create keyboard for listing available graph quests."""
        builder = InlineKeyboardBuilder()

        for quest in quests:
            builder.button(
                text=f"🎯 {quest['title']}",
                callback_data=f"graph_quest_start:{quest['id']}"
            )

        builder.button(
            text="🔄 Refresh",
            callback_data="graph_quest_refresh"
        )

        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def graph_quest_completion_keyboard(quest_id: int) -> InlineKeyboardMarkup:
        """Create keyboard for graph quest completion."""
        builder = InlineKeyboardBuilder()

        builder.button(
            text="🎯 Other Quests",
            callback_data="graph_quest_list"
        )
        builder.button(
            text="📊 My Stats",
            callback_data="graph_quest_stats"
        )
        builder.button(
            text="🗺️ View Quest Map",
            callback_data=f"graph_quest_map:{quest_id}"
        )

        builder.adjust(1)
        return builder.as_markup()


class BountyKeyboardBuilder:
    """Inline keyboards for bounty board interactions."""

    @staticmethod
    def bounty_list_keyboard(bounties: List[Dict[str, object]]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for bounty in bounties:
            payload = bounty.get('payload', {}) if isinstance(bounty, dict) else {}
            title = payload.get('title') or bounty.get('title') or 'Bounty'
            builder.button(
                text=f"🎯 {title}",
                callback_data=f"bounty_view:{bounty['id']}"
            )

        builder.button(text="🔄 Оновити", callback_data="bounty_refresh")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def bounty_detail_keyboard(bounty_id: int, accepted: bool) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if not accepted:
            builder.button(
                text="✅ Прийняти",
                callback_data=f"bounty_accept:{bounty_id}"
            )
        else:
            builder.button(
                text="🏁 Завершити",
                callback_data=f"bounty_complete:{bounty_id}"
            )
        builder.button(
            text="⬅️ Назад",
            callback_data="bounty_back"
        )
        builder.adjust(1, 1)
        return builder.as_markup()
    
class TownKeyboardBuilder:
    """Custom keyboard builder for town/location interactions."""
    
    @staticmethod
    def town_main_keyboard(town_id: int) -> InlineKeyboardMarkup:
        """
        Create main town navigation keyboard.
        
        Args:
            town_id: ID of the town
            
        Returns:
            InlineKeyboardMarkup with main town options
        """
        builder = InlineKeyboardBuilder()
        
        # Explore town button
        builder.button(
            text="🏘️ Explore Town",
            callback_data=f"town_explore:{town_id}"
        )
        
        # Town map button
        builder.button(
            text="🗺️ Town Map",
            callback_data=f"town_map:{town_id}"
        )
        
        # Town info button
        builder.button(
            text="ℹ️ Town Info",
            callback_data=f"town_info:{town_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 1)
        
        return builder.as_markup()
    
    @staticmethod
    def town_node_keyboard(
        town_id: int, 
        node_id: int, 
        connections: list[object],
        node_names: dict[int, str] = None
    ) -> InlineKeyboardMarkup:
        """
        Create keyboard for town node with available connections.
        
        Args:
            town_id: ID of the town
            node_id: ID of the current node
            connections: List of TownConnection objects
            node_names: Dictionary mapping node_id to node_name
            
        Returns:
            InlineKeyboardMarkup with navigation options
        """
        builder = InlineKeyboardBuilder()
        
        # Add connection buttons for each available path
        for connection in connections:
            # Use node name if available, otherwise fallback to node ID
            if node_names and connection.to_node_id in node_names:
                button_text = f"🚶 {node_names[connection.to_node_id]}"
            else:
                button_text = f"🚶 Go to Node {connection.to_node_id}"
            
            builder.button(
                text=button_text,
                callback_data=f"town_move:{town_id}:{node_id}:{connection.to_node_id}"
            )
        
        # Add node-specific actions
        builder.button(
            text="🔍 Explore Here",
            callback_data=f"town_explore_node:{town_id}:{node_id}"
        )
        
        # Add town map button
        builder.button(
            text="🗺️ Town Map",
            callback_data=f"town_map:{town_id}"
        )
        
        # Add back to town center button
        builder.button(
            text="🏠 Town Center",
            callback_data=f"town_center:{town_id}"
        )
        
        # Adjust layout - 1 button per row for better text visibility
        if connections:
            builder.adjust(1, 1, 2)  # connections in separate rows, then actions
        else:
            builder.adjust(1, 2)
        
        return builder.as_markup()
    
    @staticmethod
    def guild_keyboard(town_id: int, node_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for Thieves Guild node.
        
        Args:
            town_id: ID of the town
            node_id: ID of the guild node
            
        Returns:
            InlineKeyboardMarkup with guild options
        """
        builder = InlineKeyboardBuilder()
        
        # Quest board button
        builder.button(
            text="📋 Quest Board",
            callback_data=f"guild_quests:{town_id}:{node_id}"
        )
        
        # Talk to adventurers button
        builder.button(
            text="🗣️ Talk to Adventurers",
            callback_data=f"guild_talk:{town_id}:{node_id}"
        )
        
        # Guild services button
        builder.button(
            text="⚔️ Guild Services",
            callback_data=f"guild_services:{town_id}:{node_id}"
        )
        
        # Leave guild button
        builder.button(
            text="🚪 Leave Guild",
            callback_data=f"town_leave_building:{town_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 2)
        
        return builder.as_markup()
    
    @staticmethod
    def barracks_keyboard(town_id: int, node_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for Guard Barracks node.
        
        Args:
            town_id: ID of the town
            node_id: ID of the barracks node
            
        Returns:
            InlineKeyboardMarkup with barracks options
        """
        builder = InlineKeyboardBuilder()
        
        # Monster hunting board button
        builder.button(
            text="👹 Monster Hunting",
            callback_data=f"barracks_monsters:{town_id}:{node_id}"
        )
        
        # Caravan escort button
        builder.button(
            text="🚛 Caravan Escort",
            callback_data=f"barracks_escort:{town_id}:{node_id}"
        )
        
        # Guard duty button
        builder.button(
            text="🛡️ Guard Duty",
            callback_data=f"barracks_guard:{town_id}:{node_id}"
        )
        
        # Leave barracks button
        builder.button(
            text="🚪 Leave Barracks",
            callback_data=f"town_leave_building:{town_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 2)
        
        return builder.as_markup()
    
    @staticmethod
    def square_keyboard(town_id: int, node_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for Town Square node.
        
        Args:
            town_id: ID of the town
            node_id: ID of the square node
            
        Returns:
            InlineKeyboardMarkup with square options
        """
        builder = InlineKeyboardBuilder()
        
        # Talk to townspeople button
        builder.button(
            text="🗣️ Talk to Townspeople",
            callback_data=f"square_talk:{town_id}:{node_id}"
        )
        
        # Check for events button
        builder.button(
            text="📢 Check Events",
            callback_data=f"square_events:{town_id}:{node_id}"
        )
        
        # Market button
        builder.button(
            text="🏪 Market",
            callback_data=f"square_market:{town_id}:{node_id}"
        )
        
        # Leave square button
        builder.button(
            text="🚪 Leave Square",
            callback_data=f"town_leave_building:{town_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 2)
        
        return builder.as_markup()
    
    @staticmethod
    def inn_keyboard(town_id: int, node_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for Inn/Rest node.
        
        Args:
            town_id: ID of the town
            node_id: ID of the inn node
            
        Returns:
            InlineKeyboardMarkup with inn options
        """
        builder = InlineKeyboardBuilder()
        
        # Rest button
        builder.button(
            text="😴 Rest",
            callback_data=f"inn_rest:{town_id}:{node_id}"
        )
        
        # Save game button
        builder.button(
            text="💾 Save Game",
            callback_data=f"inn_save:{town_id}:{node_id}"
        )
        
        # Talk to innkeeper button
        builder.button(
            text="🗣️ Talk to Innkeeper",
            callback_data=f"inn_talk:{town_id}:{node_id}"
        )
        
        # Hero menu button
        builder.button(
            text="👤 Hero Menu",
            callback_data=f"hero_menu_from_inn:{town_id}:{node_id}"
        )
        
        # Leave inn button
        builder.button(
            text="🚪 Leave Inn",
            callback_data=f"town_leave_building:{town_id}:{node_id}"
        )
        
        # Adjust layout - 2 buttons per row for better visibility
        builder.adjust(2, 2, 1)
        
        return builder.as_markup()
    
    @staticmethod
    def town_map_keyboard(town_id: int, nodes: list[object]) -> InlineKeyboardMarkup:
        """
        Create keyboard for town map with all available nodes.
        
        Args:
            town_id: ID of the town
            nodes: List of TownNode objects
            
        Returns:
            InlineKeyboardMarkup with map navigation
        """
        builder = InlineKeyboardBuilder()
        
        # Add buttons for each accessible node
        for node in nodes:
            if node.is_accessible:
                # Use appropriate emoji based on node type
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
                
                builder.button(
                    text=f"{emoji} {node.name}",
                    callback_data=f"town_go_to:{town_id}:{node.id}"
                )
        
        # Add back to town center button
        builder.button(
            text="🏠 Town Center",
            callback_data=f"town_center:{town_id}"
        )
        
        # Adjust layout to 2 buttons per row
        builder.adjust(2)
        
        return builder.as_markup()


async def create_town_keyboard(connections, current_node_id: int):
    """Legacy helper to build town keyboards for existing imports."""
    from app.database import AsyncSessionLocal, get_town_node_by_id

    async with AsyncSessionLocal() as session:
        current_node = await get_town_node_by_id(session, current_node_id)

        if current_node:
            town_id = current_node.town_id

            if current_node.node_type == "guild":
                return TownKeyboardBuilder.guild_keyboard(town_id, current_node.id)
            if current_node.node_type == "barracks":
                return TownKeyboardBuilder.barracks_keyboard(town_id, current_node.id)
            if current_node.node_type == "square":
                return TownKeyboardBuilder.square_keyboard(town_id, current_node.id)
            if current_node.node_type == "inn":
                return TownKeyboardBuilder.inn_keyboard(town_id, current_node.id)
        else:
            town_id = 1

        node_names: dict[int, str] = {}
        for connection in connections:
            target_node = await get_town_node_by_id(session, connection.to_node_id)
            if target_node:
                node_names[connection.to_node_id] = target_node.name

        return TownKeyboardBuilder.town_node_keyboard(
            town_id=town_id,
            node_id=current_node_id,
            connections=connections,
            node_names=node_names,
        )


class CombatKeyboardBuilder:
    """Custom keyboard builder for combat interactions."""
    
    @staticmethod
    def combat_action_keyboard() -> InlineKeyboardMarkup:
        """
        Create keyboard with combat action buttons.
        
        Returns:
            InlineKeyboardMarkup with combat action buttons
        """
        builder = InlineKeyboardBuilder()
        
        # Attack button
        builder.button(
            text="⚔️ Attack",
            callback_data="combat_attack"
        )
        
        # Magic button
        builder.button(
            text="🔮 Magic",
            callback_data="combat_magic"
        )
        
        # Defend button
        builder.button(
            text="🛡️ Defend",
            callback_data="combat_defend"
        )

        # Inventory button
        builder.button(
            text="🎒 Inventory",
            callback_data="combat_inventory"
        )

        # Flee button
        builder.button(
            text="🏃 Flee",
            callback_data="combat_flee"
        )

        # Adjust layout to 2 buttons per row
        builder.adjust(2, 2, 1)

        return builder.as_markup()
    
    @staticmethod
    def combat_status_keyboard() -> InlineKeyboardMarkup:
        """
        Create keyboard for combat status display.
        
        Returns:
            InlineKeyboardMarkup with status options
        """
        builder = InlineKeyboardBuilder()
        
        # Combat status button
        builder.button(
            text="📊 Combat Status",
            callback_data="combat_status"
        )
        
        # End combat button
        builder.button(
            text="❌ End Combat",
            callback_data="combat_end"
        )
        
        # Adjust layout
        builder.adjust(1)
        
        return builder.as_markup()


# Convenience functions for easy access
def get_combat_keyboard() -> InlineKeyboardMarkup:
    """Get combat action keyboard."""
    return CombatKeyboardBuilder.combat_action_keyboard()


def get_combat_status_keyboard() -> InlineKeyboardMarkup:
    """Get combat status keyboard."""
    return CombatKeyboardBuilder.combat_status_keyboard()


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    builder = InlineKeyboardBuilder()
    
    # Hero stats button
    builder.button(
        text="👤 Hero Stats",
        callback_data="hero_stats"
    )
    
    # Start fight button
    builder.button(
        text="⚔️ Start Fight",
        callback_data="start_fight"
    )
    
    # Quests button
    builder.button(
        text="🎯 Quests",
        callback_data="quest_list"
    )
    
    # Towns button
    builder.button(
        text="🏘️ Towns",
        callback_data="town_list"
    )
    
    # Adjust layout to 2 buttons per row
    builder.adjust(2, 2)
    
    return builder.as_markup()
