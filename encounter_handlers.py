"""
Encounter handlers for integrating encounter system with quests and combat.
"""

import logging
from typing import Optional, Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic

from database import (
    AsyncSessionLocal,
    get_user_by_telegram_id,
    get_hero_by_user_id,
    get_hero_class_by_id,
    get_monster_class_by_name,
    create_monster
)
from encounter_system import encounter_engine, EncounterResult
from combat_system import combat_engine, CombatAction
from keyboards import CombatKeyboardBuilder

logger = logging.getLogger(__name__)

# Create router for encounter handlers
encounter_router = Router()


class EncounterManager:
    """Manager for handling encounters in quests."""
    
    @staticmethod
    async def trigger_encounter(
        user_id: int, 
        quest_node_data: Dict[str, Any]
    ) -> Optional[EncounterResult]:
        """
        Trigger an encounter for a quest node.
        
        Args:
            user_id: Telegram user ID
            quest_node_data: Quest node data with encounter_tags
            
        Returns:
            EncounterResult if encounter should happen, None otherwise
        """
        async with AsyncSessionLocal() as session:
            # Get user and hero
            user = await get_user_by_telegram_id(session, user_id)
            if not user:
                return None
            
            hero = await get_hero_by_user_id(session, user_id)
            if not hero:
                return None
            
            # Check if node has encounter tags
            encounter_tags = quest_node_data.get('encounter_tags')
            if not encounter_tags:
                return None
            
            # Generate encounter
            encounter = await encounter_engine.get_encounter_for_quest_node(
                hero.level, quest_node_data
            )
            
            if not encounter:
                return None
            
            return encounter
    
    @staticmethod
    async def start_encounter_combat(
        user_id: int, 
        encounter: EncounterResult
    ) -> bool:
        """
        Start combat for an encounter.
        
        Args:
            user_id: Telegram user ID
            encounter: Encounter result with monster info
            
        Returns:
            True if combat started successfully, False otherwise
        """
        async with AsyncSessionLocal() as session:
            # Get user and hero
            user = await get_user_by_telegram_id(session, user_id)
            if not user:
                return False
            
            hero = await get_hero_by_user_id(session, user_id)
            if not hero:
                return False
            
            hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
            if not hero_class:
                return False
            
            # Get monster class
            monster_class = await get_monster_class_by_name(session, encounter.monster_name)
            if not monster_class:
                return False
            
            # Create monster instance
            monster = await create_monster(
                session=session,
                monster_class_id=monster_class.id,
                name=encounter.monster_name,
                level=hero.level,  # Scale to hero level
                location=f"Quest Encounter - {encounter.biome.value}"
            )
            
            # Start combat
            combat_state = combat_engine.start_combat(
                user_id=user_id,
                hero=hero,
                hero_class=hero_class,
                monster=monster,
                monster_class=monster_class
            )
            
            # Apply encounter modifiers
            if encounter.special_modifiers:
                await EncounterManager._apply_encounter_modifiers(
                    combat_state, encounter.special_modifiers
                )
            
            return True
    
    @staticmethod
    async def _apply_encounter_modifiers(
        combat_state, 
        modifiers: Dict[str, Any]
    ):
        """Apply special modifiers to combat state."""
        # Apply ambush bonus to monster
        if 'ambush_bonus' in modifiers:
            bonus = modifiers['ambush_bonus']
            combat_state.monster_stats.atk = int(combat_state.monster_stats.atk * (1 + bonus))
            combat_state.monster_stats.mag = int(combat_state.monster_stats.mag * (1 + bonus))
        
        # Apply boss bonus to monster
        if 'boss_bonus' in modifiers:
            bonus = modifiers['boss_bonus']
            combat_state.monster_stats.atk = int(combat_state.monster_stats.atk * (1 + bonus))
            combat_state.monster_stats.mag = int(combat_state.monster_stats.mag * (1 + bonus))
            combat_state.monster_stats.hp_max = int(combat_state.monster_stats.hp_max * (1 + bonus))
            combat_state.monster_hp = combat_state.monster_stats.hp_max
        
        # Apply hero penalties
        if 'hero_penalty' in modifiers:
            penalty = modifiers['hero_penalty']
            combat_state.hero_stats.atk = int(combat_state.hero_stats.atk * (1 - penalty))
            combat_state.hero_stats.mag = int(combat_state.hero_stats.mag * (1 - penalty))
    
    @staticmethod
    def format_encounter_message(encounter: EncounterResult) -> str:
        """Format encounter message for display."""
        message = f"⚔️ {hbold('ENCOUNTER!')}\n\n"
        
        # Add encounter type flavor
        if encounter.is_ambush:
            message += f"💥 {hitalic('AMBUSH!')} You are caught off guard!\n\n"
        elif encounter.is_boss:
            message += f"👑 {hitalic('BOSS BATTLE!')} A powerful foe blocks your path!\n\n"
        else:
            message += f"👹 A {encounter.monster_name} appears!\n\n"
        
        # Add biome context
        biome_names = {
            'forest': '🌲 Forest',
            'cave': '🕳️ Cave',
            'dungeon': '🏰 Dungeon',
            'mountain': '⛰️ Mountain',
            'swamp': '🐸 Swamp',
            'desert': '🏜️ Desert',
            'ruins': '🏛️ Ruins',
            'tower': '🗼 Tower'
        }
        
        biome_name = biome_names.get(encounter.biome.value, encounter.biome.value.title())
        message += f"📍 Location: {biome_name}\n"
        message += f"⚡ Difficulty: {encounter.difficulty.value.title()}\n\n"
        
        # Add special modifiers info
        if encounter.special_modifiers:
            if 'ambush_bonus' in encounter.special_modifiers:
                message += f"⚠️ {hitalic('Ambush: Monster has +20% stats!')}\n"
            if 'boss_bonus' in encounter.special_modifiers:
                message += f"👑 {hitalic('Boss: Monster has +50% stats!')}\n"
            if 'darkness_penalty' in encounter.special_modifiers:
                message += f"🌑 {hitalic('Darkness: -5% accuracy penalty!')}\n"
            if 'poison_chance' in encounter.special_modifiers:
                message += f"☠️ {hitalic('Poisonous environment!')}\n"
        
        message += f"\n{hbold('Prepare for battle!')}"
        
        return message


# Encounter callback handlers
@encounter_router.callback_query(F.data.startswith("encounter_combat:"))
async def handle_encounter_combat(callback: CallbackQuery):
    """Handle encounter combat callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = parts[2]
    user_id = callback.from_user.id
    
    # Get quest node data (this would need to be passed or retrieved)
    # For now, we'll create a simple encounter
    quest_node_data = {
        'id': node_id,
        'quest_id': quest_id,
        'encounter_tags': {
            'biome': 'cave',
            'difficulty': 'normal',
            'type': 'combat'
        }
    }
    
    # Trigger encounter
    encounter = await EncounterManager.trigger_encounter(user_id, quest_node_data)
    
    if not encounter:
        await callback.answer("No encounter found for this location.", show_alert=True)
        return
    
    # Start combat
    combat_started = await EncounterManager.start_encounter_combat(user_id, encounter)
    
    if not combat_started:
        await callback.answer("Failed to start combat.", show_alert=True)
        return
    
    # Get combat state
    combat_state = combat_engine.get_combat_state(user_id)
    if not combat_state:
        await callback.answer("Combat state not found.", show_alert=True)
        return
    
    # Format encounter and combat messages
    encounter_message = EncounterManager.format_encounter_message(encounter)
    combat_status = combat_engine.format_combat_status(combat_state)
    
    full_message = f"{encounter_message}\n\n{combat_status}"
    
    # Create combat keyboard
    keyboard = CombatKeyboardBuilder.combat_keyboard()
    
    await callback.message.edit_text(full_message, reply_markup=keyboard)
    await callback.answer()


@encounter_router.callback_query(F.data.startswith("encounter_flee:"))
async def handle_encounter_flee(callback: CallbackQuery):
    """Handle encounter flee callback."""
    user_id = callback.from_user.id
    
    # Check if user is in combat
    combat_state = combat_engine.get_combat_state(user_id)
    if not combat_state:
        await callback.answer("You are not in combat.", show_alert=True)
        return
    
    # Try to flee
    flee_result = combat_engine.execute_hero_action(user_id, CombatAction.FLEE)
    
    if flee_result and "успішно втік" in flee_result.message:
        # Successfully fled
        await callback.message.edit_text(
            f"🏃 {hbold('Fled from encounter!')}\n\n"
            f"You successfully escaped from the battle."
        )
    else:
        # Failed to flee, show combat status
        combat_status = combat_engine.format_combat_status(combat_state)
        keyboard = CombatKeyboardBuilder.combat_keyboard()
        
        await callback.message.edit_text(combat_status, reply_markup=keyboard)
    
    await callback.answer()


def register_encounter_handlers(dp):
    """Register encounter handlers with the dispatcher."""
    dp.include_router(encounter_router)
    logger.info("Encounter handlers registered successfully")
