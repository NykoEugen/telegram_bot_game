"""
Test script for Encounter System.
"""

import asyncio
import logging
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from app.core.encounter_system import (
    encounter_engine,
    EncounterContext,
    Biome,
    Difficulty,
    EncounterType,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_encounter_generation():
    """Test basic encounter generation."""
    print("🧪 Testing Encounter Generation...")
    
    # Test 1: Easy cave encounter
    context1 = EncounterContext(
        hero_level=5,
        biome=Biome.CAVE,
        difficulty=Difficulty.EASY,
        encounter_type=EncounterType.COMBAT
    )
    
    encounter1 = await encounter_engine.generate_encounter(context1)
    if encounter1:
        print(f"✅ Easy Cave Encounter: {encounter1.monster_name} ({encounter1.difficulty.value})")
    else:
        print("❌ Failed to generate easy cave encounter")
    
    # Test 2: Boss encounter
    context2 = EncounterContext(
        hero_level=10,
        biome=Biome.ANY,
        difficulty=Difficulty.BOSS,
        encounter_type=EncounterType.BOSS
    )
    
    encounter2 = await encounter_engine.generate_encounter(context2)
    if encounter2:
        print(f"✅ Boss Encounter: {encounter2.monster_name} ({encounter2.difficulty.value})")
        print(f"   Special modifiers: {encounter2.special_modifiers}")
    else:
        print("❌ Failed to generate boss encounter")
    
    # Test 3: Ambush encounter
    context3 = EncounterContext(
        hero_level=7,
        biome=Biome.FOREST,
        difficulty=Difficulty.NORMAL,
        encounter_type=EncounterType.AMBUSH
    )
    
    encounter3 = await encounter_engine.generate_encounter(context3)
    if encounter3:
        print(f"✅ Ambush Encounter: {encounter3.monster_name} ({encounter3.difficulty.value})")
        print(f"   Is ambush: {encounter3.is_ambush}")
        print(f"   Special modifiers: {encounter3.special_modifiers}")
    else:
        print("❌ Failed to generate ambush encounter")


async def test_quest_node_encounter():
    """Test encounter generation from quest node data."""
    print("\n🧪 Testing Quest Node Encounter...")
    
    # Simulate quest node data
    quest_node_data = {
        'id': 'test_node',
        'quest_id': 2,
        'encounter_tags': {
            'biome': 'cave',
            'difficulty': 'normal',
            'type': 'combat',
            'special_tags': ['test']
        }
    }
    
    encounter = await encounter_engine.get_encounter_for_quest_node(
        hero_level=8, 
        quest_node_data=quest_node_data
    )
    
    if encounter:
        print(f"✅ Quest Node Encounter: {encounter.monster_name}")
        print(f"   Biome: {encounter.biome.value}")
        print(f"   Difficulty: {encounter.difficulty.value}")
        print(f"   Type: {encounter.encounter_type.value}")
    else:
        print("❌ Failed to generate quest node encounter")


async def test_encounter_rules():
    """Test encounter rules selection."""
    print("\n🧪 Testing Encounter Rules...")
    
    from app.core.encounter_system import EncounterRules
    
    # Test rule selection for different contexts
    contexts = [
        EncounterContext(5, Biome.FOREST, Difficulty.EASY, EncounterType.COMBAT),
        EncounterContext(10, Biome.CAVE, Difficulty.HARD, EncounterType.COMBAT),
        EncounterContext(15, Biome.ANY, Difficulty.BOSS, EncounterType.BOSS),
    ]
    
    for i, context in enumerate(contexts, 1):
        rules = EncounterRules.get_applicable_rules(context)
        print(f"✅ Context {i}: Found {len(rules)} applicable rules")
        for rule in rules:
            print(f"   - {rule.biome.value} + {rule.difficulty.value} + {rule.encounter_type.value} (weight: {rule.weight})")


async def main():
    """Run all tests."""
    print("🚀 Starting Encounter System Tests...\n")
    
    try:
        await test_encounter_generation()
        await test_quest_node_encounter()
        await test_encounter_rules()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test error details:")


if __name__ == "__main__":
    asyncio.run(main())
