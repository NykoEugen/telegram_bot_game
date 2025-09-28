"""
Encounter System for dynamic monster selection in quests.
Decouples quests from specific monsters through encounter rules.
"""

import random
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from database import AsyncSessionLocal, get_monster_class_by_name, get_monster_classes_by_criteria
from hero_system import HeroCalculator
from monster_system import MonsterCalculator


class EncounterType(Enum):
    """Types of encounters."""
    COMBAT = "combat"
    AMBUSH = "ambush"
    BOSS = "boss"
    RANDOM = "random"


class Biome(Enum):
    """Biome types for encounter selection."""
    FOREST = "forest"
    CAVE = "cave"
    DUNGEON = "dungeon"
    MOUNTAIN = "mountain"
    SWAMP = "swamp"
    DESERT = "desert"
    RUINS = "ruins"
    TOWER = "tower"
    ANY = "any"


class Difficulty(Enum):
    """Difficulty levels for encounters."""
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    BOSS = "boss"


@dataclass
class EncounterRule:
    """Rule for selecting monsters in encounters."""
    biome: Biome
    difficulty: Difficulty
    encounter_type: EncounterType
    monster_types: List[str]  # Allowed monster types
    min_level: int = 1
    max_level: int = 100
    weight: int = 100  # Selection weight
    special_conditions: Dict[str, Any] = None  # Additional conditions


@dataclass
class EncounterContext:
    """Context for encounter generation."""
    hero_level: int
    biome: Biome
    difficulty: Difficulty
    encounter_type: EncounterType
    quest_id: Optional[int] = None
    node_id: Optional[str] = None
    special_tags: List[str] = None  # Additional tags from quest node


@dataclass
class EncounterResult:
    """Result of encounter generation."""
    monster_name: str
    monster_class: str
    encounter_type: EncounterType
    biome: Biome
    difficulty: Difficulty
    is_ambush: bool = False
    is_boss: bool = False
    special_modifiers: Dict[str, Any] = None


class EncounterRules:
    """Predefined encounter rules for different scenarios."""
    
    # Base rules for different biomes and difficulties
    RULES = [
        # Forest encounters
        EncounterRule(
            biome=Biome.FOREST,
            difficulty=Difficulty.EASY,
            encounter_type=EncounterType.COMBAT,
            monster_types=["beast", "humanoid"],
            weight=100
        ),
        EncounterRule(
            biome=Biome.FOREST,
            difficulty=Difficulty.NORMAL,
            encounter_type=EncounterType.COMBAT,
            monster_types=["beast", "humanoid", "elemental"],
            weight=80
        ),
        EncounterRule(
            biome=Biome.FOREST,
            difficulty=Difficulty.HARD,
            encounter_type=EncounterType.COMBAT,
            monster_types=["beast", "elemental", "demon"],
            weight=60
        ),
        
        # Cave encounters
        EncounterRule(
            biome=Biome.CAVE,
            difficulty=Difficulty.EASY,
            encounter_type=EncounterType.COMBAT,
            monster_types=["beast", "undead"],
            weight=100
        ),
        EncounterRule(
            biome=Biome.CAVE,
            difficulty=Difficulty.NORMAL,
            encounter_type=EncounterType.COMBAT,
            monster_types=["undead", "humanoid", "beast"],
            weight=80
        ),
        EncounterRule(
            biome=Biome.CAVE,
            difficulty=Difficulty.HARD,
            encounter_type=EncounterType.COMBAT,
            monster_types=["undead", "demon", "elemental"],
            weight=60
        ),
        
        # Dungeon encounters
        EncounterRule(
            biome=Biome.DUNGEON,
            difficulty=Difficulty.EASY,
            encounter_type=EncounterType.COMBAT,
            monster_types=["undead", "humanoid"],
            weight=100
        ),
        EncounterRule(
            biome=Biome.DUNGEON,
            difficulty=Difficulty.NORMAL,
            encounter_type=EncounterType.COMBAT,
            monster_types=["undead", "humanoid", "demon"],
            weight=80
        ),
        EncounterRule(
            biome=Biome.DUNGEON,
            difficulty=Difficulty.HARD,
            encounter_type=EncounterType.COMBAT,
            monster_types=["demon", "undead", "elemental"],
            weight=60
        ),
        
        # Boss encounters
        EncounterRule(
            biome=Biome.ANY,
            difficulty=Difficulty.BOSS,
            encounter_type=EncounterType.BOSS,
            monster_types=["beast", "undead", "demon", "elemental"],
            weight=100
        ),
        
        # Ambush encounters
        EncounterRule(
            biome=Biome.ANY,
            difficulty=Difficulty.NORMAL,
            encounter_type=EncounterType.AMBUSH,
            monster_types=["humanoid", "beast", "demon"],
            weight=30
        ),
        
        # Random encounters (can happen anywhere)
        EncounterRule(
            biome=Biome.ANY,
            difficulty=Difficulty.EASY,
            encounter_type=EncounterType.RANDOM,
            monster_types=["beast", "humanoid", "undead"],
            weight=20
        ),
    ]
    
    @classmethod
    def get_applicable_rules(cls, context: EncounterContext) -> List[EncounterRule]:
        """Get rules applicable to the given context."""
        applicable_rules = []
        
        for rule in cls.RULES:
            # Check biome match
            if rule.biome != Biome.ANY and rule.biome != context.biome:
                continue
            
            # Check difficulty match
            if rule.difficulty != context.difficulty:
                continue
            
            # Check encounter type match
            if rule.encounter_type != context.encounter_type:
                continue
            
            # Check level range
            if not (rule.min_level <= context.hero_level <= rule.max_level):
                continue
            
            applicable_rules.append(rule)
        
        return applicable_rules


class EncounterEngine:
    """Main engine for generating encounters."""
    
    def __init__(self):
        self.rules = EncounterRules()
    
    async def generate_encounter(self, context: EncounterContext) -> Optional[EncounterResult]:
        """
        Generate an encounter based on context.
        
        Args:
            context: Encounter context with hero level, biome, etc.
            
        Returns:
            EncounterResult with selected monster, or None if no suitable monster found
        """
        # Get applicable rules
        applicable_rules = self.rules.get_applicable_rules(context)
        
        if not applicable_rules:
            return None
        
        # Select rule based on weights
        selected_rule = self._select_rule_by_weight(applicable_rules)
        
        # Get available monsters for this rule
        async with AsyncSessionLocal() as session:
            available_monsters = await get_monster_classes_by_criteria(
                session,
                monster_types=selected_rule.monster_types,
                difficulty=selected_rule.difficulty.value
            )
        
        if not available_monsters:
            return None
        
        # Select monster based on hero level and other factors
        selected_monster = self._select_monster_by_level(
            available_monsters, context.hero_level, selected_rule
        )
        
        if not selected_monster:
            return None
        
        # Create encounter result
        result = EncounterResult(
            monster_name=selected_monster.name,
            monster_class=selected_monster.name,
            encounter_type=context.encounter_type,
            biome=context.biome,
            difficulty=context.difficulty,
            is_ambush=(context.encounter_type == EncounterType.AMBUSH),
            is_boss=(context.difficulty == Difficulty.BOSS),
            special_modifiers=self._generate_special_modifiers(context, selected_rule)
        )
        
        return result
    
    def _select_rule_by_weight(self, rules: List[EncounterRule]) -> EncounterRule:
        """Select a rule based on weights."""
        weights = [rule.weight for rule in rules]
        return random.choices(rules, weights=weights)[0]
    
    def _select_monster_by_level(
        self, 
        monsters: List, 
        hero_level: int, 
        rule: EncounterRule
    ) -> Optional[Any]:
        """Select monster based on hero level and rule constraints."""
        if not monsters:
            return None
        
        # Filter monsters by level appropriateness
        suitable_monsters = []
        for monster in monsters:
            # Calculate monster level based on difficulty
            monster_level = self._calculate_monster_level(monster, rule.difficulty)
            
            # Check if monster level is appropriate for hero
            if self._is_level_appropriate(monster_level, hero_level, rule.difficulty):
                suitable_monsters.append(monster)
        
        if not suitable_monsters:
            # Fallback to any available monster
            suitable_monsters = monsters
        
        return random.choice(suitable_monsters)
    
    def _calculate_monster_level(self, monster, difficulty: Difficulty) -> int:
        """Calculate effective monster level based on difficulty."""
        # Base level calculation from monster stats
        base_level = (monster.base_str + monster.base_agi + 
                     monster.base_int + monster.base_vit + monster.base_luk) // 5
        
        # Adjust for difficulty
        if difficulty == Difficulty.EASY:
            return max(1, base_level - 2)
        elif difficulty == Difficulty.NORMAL:
            return base_level
        elif difficulty == Difficulty.HARD:
            return base_level + 2
        elif difficulty == Difficulty.BOSS:
            return base_level + 5
        
        return base_level
    
    def _is_level_appropriate(
        self, 
        monster_level: int, 
        hero_level: int, 
        difficulty: Difficulty
    ) -> bool:
        """Check if monster level is appropriate for hero level."""
        level_diff = abs(monster_level - hero_level)
        
        if difficulty == Difficulty.EASY:
            return level_diff <= 3
        elif difficulty == Difficulty.NORMAL:
            return level_diff <= 5
        elif difficulty == Difficulty.HARD:
            return level_diff <= 7
        elif difficulty == Difficulty.BOSS:
            return level_diff <= 10
        
        return level_diff <= 5
    
    def _generate_special_modifiers(
        self, 
        context: EncounterContext, 
        rule: EncounterRule
    ) -> Dict[str, Any]:
        """Generate special modifiers for the encounter."""
        modifiers = {}
        
        # Ambush modifiers
        if context.encounter_type == EncounterType.AMBUSH:
            modifiers['ambush_bonus'] = 0.2  # 20% bonus to monster stats
            modifiers['hero_penalty'] = 0.1  # 10% penalty to hero stats
        
        # Boss modifiers
        if context.difficulty == Difficulty.BOSS:
            modifiers['boss_bonus'] = 0.5  # 50% bonus to monster stats
            modifiers['special_abilities'] = True
        
        # Biome-specific modifiers
        if context.biome == Biome.CAVE:
            modifiers['darkness_penalty'] = 0.05  # 5% penalty to accuracy
        elif context.biome == Biome.SWAMP:
            modifiers['poison_chance'] = 0.1  # 10% chance of poison
        
        return modifiers
    
    async def get_encounter_for_quest_node(
        self, 
        hero_level: int, 
        quest_node_data: Dict[str, Any]
    ) -> Optional[EncounterResult]:
        """
        Generate encounter for a specific quest node.
        
        Args:
            hero_level: Hero's current level
            quest_node_data: Quest node data with encounter tags
            
        Returns:
            EncounterResult or None
        """
        # Extract encounter context from quest node
        context = self._parse_quest_node_context(hero_level, quest_node_data)
        
        if not context:
            return None
        
        return await self.generate_encounter(context)
    
    def _parse_quest_node_context(
        self, 
        hero_level: int, 
        quest_node_data: Dict[str, Any]
    ) -> Optional[EncounterContext]:
        """Parse quest node data to create encounter context."""
        # Check if node has encounter tags
        encounter_tags = quest_node_data.get('encounter_tags', {})
        
        if not encounter_tags:
            return None
        
        # Parse biome
        biome_str = encounter_tags.get('biome', 'any')
        try:
            biome = Biome(biome_str)
        except ValueError:
            biome = Biome.ANY
        
        # Parse difficulty
        difficulty_str = encounter_tags.get('difficulty', 'normal')
        try:
            difficulty = Difficulty(difficulty_str)
        except ValueError:
            difficulty = Difficulty.NORMAL
        
        # Parse encounter type
        encounter_type_str = encounter_tags.get('type', 'combat')
        try:
            encounter_type = EncounterType(encounter_type_str)
        except ValueError:
            encounter_type = EncounterType.COMBAT
        
        # Parse special tags
        special_tags = encounter_tags.get('special_tags', [])
        
        return EncounterContext(
            hero_level=hero_level,
            biome=biome,
            difficulty=difficulty,
            encounter_type=encounter_type,
            quest_id=quest_node_data.get('quest_id'),
            node_id=quest_node_data.get('id'),
            special_tags=special_tags
        )


# Global encounter engine instance
encounter_engine = EncounterEngine()
