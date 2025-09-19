"""
Test script for combat system.
"""

import asyncio
import logging
from database import get_db_session, get_hero_by_user_id, get_hero_class_by_id
from hero_system import HeroCalculator
from monster_system import MonsterCalculator
from combat_system import combat_engine, CombatAction, CombatResult
from init_monsters import create_sample_monster

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_combat_system():
    """Test the combat system with a sample hero and monster."""
    logger.info("Starting combat system test...")
    
    async with get_db_session() as session:
        try:
            # Get a test hero (assuming user_id 1 exists)
            hero = await get_hero_by_user_id(session, 1)
            if not hero:
                logger.error("No hero found for user_id 1. Please create a hero first.")
                return
            
            # Get hero class
            hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
            if not hero_class:
                logger.error("Hero class not found!")
                return
            
            # Create a sample monster
            monster = await create_sample_monster(session, difficulty="easy", level=1)
            monster_class = await get_monster_class_by_id(session, monster.monster_class_id)
            
            logger.info(f"Testing combat: {hero.name} vs {monster.name}")
            
            # Start combat
            combat_state = combat_engine.start_combat(1, hero, hero_class, monster, monster_class)
            logger.info("Combat started!")
            
            # Display initial status
            status = combat_engine.format_combat_status(combat_state)
            logger.info(f"Initial status:\n{status}")
            
            # Simulate a few combat rounds
            for round_num in range(1, 6):
                logger.info(f"\n--- Round {round_num} ---")
                
                # Hero action (attack)
                hero_result = combat_engine.execute_hero_action(1, CombatAction.ATTACK)
                if hero_result:
                    logger.info(f"Hero action: {hero_result.message}")
                
                # Check if combat ended
                result = combat_engine.check_combat_end(1)
                if result != CombatResult.ONGOING:
                    logger.info(f"Combat ended: {result}")
                    break
                
                # Monster action
                monster_result = combat_engine.execute_monster_action(1)
                if monster_result:
                    logger.info(f"Monster action: {monster_result.message}")
                
                # Check if combat ended
                result = combat_engine.check_combat_end(1)
                if result != CombatResult.ONGOING:
                    logger.info(f"Combat ended: {result}")
                    break
                
                # Display status
                combat_state = combat_engine.get_combat_state(1)
                if combat_state:
                    status = combat_engine.format_combat_status(combat_state)
                    logger.info(f"Status after round {round_num}:\n{status}")
            
            # Get final rewards if hero won
            final_state = combat_engine.get_combat_state(1)
            if final_state:
                rewards = combat_engine.get_combat_rewards(final_state)
                logger.info(f"Rewards: {rewards}")
            
            # Clean up
            combat_engine.end_combat(1)
            logger.info("Combat test completed!")
            
        except Exception as e:
            logger.error(f"Error during combat test: {e}")
            raise


async def test_combat_calculations():
    """Test combat calculation functions."""
    logger.info("Testing combat calculations...")
    
    # Test damage calculation
    from combat_system import CombatCalculator
    
    attacker_stats = {'atk': 10, 'mag': 8, 'crit_chance': 15.0}
    defender_stats = {'dodge': 10.0}
    
    # Test normal attack
    damage = CombatCalculator.calculate_damage(attacker_stats, defender_stats, CombatAction.ATTACK)
    logger.info(f"Normal attack damage: {damage}")
    
    # Test critical hit
    damage_crit = CombatCalculator.calculate_damage(attacker_stats, defender_stats, CombatAction.ATTACK, is_critical=True)
    logger.info(f"Critical attack damage: {damage_crit}")
    
    # Test magic attack
    magic_damage = CombatCalculator.calculate_damage(attacker_stats, defender_stats, CombatAction.MAGIC)
    logger.info(f"Magic attack damage: {magic_damage}")
    
    # Test defense reduction
    reduced_damage = CombatCalculator.calculate_defense_reduction(damage, is_defending=True)
    logger.info(f"Damage with defense: {reduced_damage}")
    
    # Test critical hit chance
    crit_hit = CombatCalculator.check_critical_hit(attacker_stats)
    logger.info(f"Critical hit: {crit_hit}")
    
    # Test dodge chance
    dodge = CombatCalculator.check_dodge(defender_stats)
    logger.info(f"Dodge: {dodge}")
    
    logger.info("Combat calculations test completed!")


if __name__ == "__main__":
    asyncio.run(test_combat_calculations())
    # Uncomment to test full combat (requires existing hero):
    # asyncio.run(test_combat_system())
