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
