"""
Custom inline keyboard builder for quest system.
"""
from typing import List, Optional
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
        """
        Create graph quest menu keyboard with various options.
        
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
            callback_data=f"graph_quest_continue:{quest_id}:{node_id}"
        )
        
        # Quest map button
        builder.button(
            text="🗺️ Quest Map",
            callback_data=f"graph_quest_map:{quest_id}"
        )
        
        # Quest progress button
        builder.button(
            text="📊 Progress",
            callback_data=f"graph_quest_progress:{quest_id}:{node_id}"
        )
        
        # Quest info button
        builder.button(
            text="ℹ️ Quest Info",
            callback_data=f"graph_quest_info:{quest_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 2)
        
        return builder.as_markup()
    
    @staticmethod
    def graph_quest_list_keyboard(quests: List[dict]) -> InlineKeyboardMarkup:
        """
        Create keyboard for listing available graph quests.
        
        Args:
            quests: List of quest dictionaries with 'id' and 'title' keys
            
        Returns:
            InlineKeyboardMarkup with quest list buttons
        """
        builder = InlineKeyboardBuilder()
        
        for quest in quests:
            builder.button(
                text=f"🎯 {quest['title']}",
                callback_data=f"graph_quest_start:{quest['id']}"
            )
        
        # Add refresh button
        builder.button(
            text="🔄 Refresh",
            callback_data="graph_quest_refresh"
        )
        
        # Adjust layout to 1 button per row
        builder.adjust(1)
        
        return builder.as_markup()
    
    @staticmethod
    def graph_quest_completion_keyboard(quest_id: int) -> InlineKeyboardMarkup:
        """
        Create keyboard for graph quest completion.
        
        Args:
            quest_id: ID of the completed quest
            
        Returns:
            InlineKeyboardMarkup with completion options
        """
        builder = InlineKeyboardBuilder()
        
        # View other quests button
        builder.button(
            text="🎯 Other Quests",
            callback_data="graph_quest_list"
        )
        
        # Quest stats button
        builder.button(
            text="📊 My Stats",
            callback_data="graph_quest_stats"
        )
        
        # Quest map button
        builder.button(
            text="🗺️ View Quest Map",
            callback_data=f"graph_quest_map:{quest_id}"
        )
        
        # Adjust layout
        builder.adjust(1)
        
        return builder.as_markup()
    
    @staticmethod
    def graph_quest_navigation_keyboard(
        quest_id: int, 
        node_id: int, 
        connections: List[object]
    ) -> InlineKeyboardMarkup:
        """
        Create navigation keyboard for graph quest progression.
        
        Args:
            quest_id: ID of the quest
            node_id: ID of the current quest node
            connections: List of available connections
            
        Returns:
            InlineKeyboardMarkup with navigation buttons
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
        
        # Adjust layout
        if connections:
            builder.adjust(len(connections), 1)
        else:
            builder.adjust(1)
        
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
        connections: list[object]
    ) -> InlineKeyboardMarkup:
        """
        Create keyboard for town node with available connections.
        
        Args:
            town_id: ID of the town
            node_id: ID of the current node
            connections: List of TownConnection objects
            
        Returns:
            InlineKeyboardMarkup with navigation options
        """
        builder = InlineKeyboardBuilder()
        
        # Add connection buttons for each available path
        for connection in connections:
            # Get the target node name (we'll need to fetch this in the handler)
            builder.button(
                text=f"🚶 Go to Node {connection.to_node_id}",
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
        
        # Adjust layout
        if connections:
            builder.adjust(len(connections), 1, 2)
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
        
        # Leave inn button
        builder.button(
            text="🚪 Leave Inn",
            callback_data=f"town_leave_building:{town_id}:{node_id}"
        )
        
        # Adjust layout
        builder.adjust(2, 2)
        
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
