"""
Combat system logic for handling battles between heroes and monsters.
"""

import random
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from database import Hero, Monster, HeroClass, MonsterClass
from hero_system import HeroStats, HeroCalculator
from monster_system import MonsterStats, MonsterCalculator


class CombatAction(Enum):
    """Available combat actions."""
    ATTACK = "attack"
    MAGIC = "magic"
    DEFEND = "defend"
    FLEE = "flee"


class CombatResult(Enum):
    """Combat result types."""
    HERO_WIN = "hero_win"
    MONSTER_WIN = "monster_win"
    HERO_FLEE = "hero_flee"
    ONGOING = "ongoing"


@dataclass
class CombatActionResult:
    """Result of a single combat action."""
    attacker: str  # "hero" or "monster"
    action: CombatAction
    damage: int
    is_critical: bool
    is_dodged: bool
    message: str


@dataclass
class CombatState:
    """Current state of a combat encounter."""
    hero_stats: HeroStats
    monster_stats: MonsterStats
    hero_hp: int
    monster_hp: int
    turn: int
    hero_defending: bool = False
    monster_defending: bool = False
    combat_log: List[str] = None
    
    def __post_init__(self):
        if self.combat_log is None:
            self.combat_log = []


class CombatCalculator:
    """Class for calculating combat mechanics."""
    
    @staticmethod
    def calculate_damage(attacker_stats: Dict[str, Any], defender_stats: Dict[str, Any], 
                        action: CombatAction, is_critical: bool = False) -> int:
        """Calculate damage dealt by an attack."""
        if action == CombatAction.ATTACK:
            base_damage = attacker_stats['atk']
        elif action == CombatAction.MAGIC:
            base_damage = attacker_stats['mag']
        else:
            return 0
        
        # Critical hit multiplier
        if is_critical:
            base_damage = int(base_damage * 1.5)
        
        # Add some randomness (±20%)
        damage_variance = random.uniform(0.8, 1.2)
        final_damage = int(base_damage * damage_variance)
        
        return max(1, final_damage)  # Minimum 1 damage
    
    @staticmethod
    def check_critical_hit(attacker_stats: Dict[str, Any]) -> bool:
        """Check if an attack is a critical hit."""
        crit_chance = attacker_stats['crit_chance']
        return random.random() * 100 < crit_chance
    
    @staticmethod
    def check_dodge(defender_stats: Dict[str, Any]) -> bool:
        """Check if an attack is dodged."""
        dodge_chance = defender_stats['dodge']
        return random.random() * 100 < dodge_chance
    
    @staticmethod
    def calculate_defense_reduction(damage: int, is_defending: bool) -> int:
        """Calculate damage reduction from defending."""
        if is_defending:
            # Defending reduces damage by 50%
            return int(damage * 0.5)
        return damage


class CombatEngine:
    """Main combat engine for handling battles."""
    
    def __init__(self):
        self.active_combats: Dict[int, CombatState] = {}  # user_id -> CombatState
    
    def start_combat(self, user_id: int, hero: Hero, hero_class: HeroClass, 
                    monster: Monster, monster_class: MonsterClass) -> CombatState:
        """Start a new combat encounter."""
        hero_stats = HeroCalculator.create_hero_stats(hero, hero_class)
        monster_stats = MonsterCalculator.create_monster_stats(monster, monster_class)
        
        combat_state = CombatState(
            hero_stats=hero_stats,
            monster_stats=monster_stats,
            hero_hp=hero_stats.hp_current,
            monster_hp=monster_stats.hp_current,
            turn=1
        )
        
        # Add initial combat message
        combat_state.combat_log.append(
            f"⚔️ Бій почався! {hero.name} проти {monster.name}!"
        )
        
        self.active_combats[user_id] = combat_state
        return combat_state
    
    def execute_hero_action(self, user_id: int, action: CombatAction) -> Optional[CombatActionResult]:
        """Execute a hero's combat action."""
        if user_id not in self.active_combats:
            return None
        
        combat_state = self.active_combats[user_id]
        
        if action == CombatAction.DEFEND:
            combat_state.hero_defending = True
            return CombatActionResult(
                attacker="hero",
                action=action,
                damage=0,
                is_critical=False,
                is_dodged=False,
                message=f"🛡️ {combat_state.hero_stats.name if hasattr(combat_state.hero_stats, 'name') else 'Герой'} захищається!"
            )
        
        if action == CombatAction.FLEE:
            # 70% chance to flee successfully
            if random.random() < 0.7:
                del self.active_combats[user_id]
                return CombatActionResult(
                    attacker="hero",
                    action=action,
                    damage=0,
                    is_critical=False,
                    is_dodged=False,
                    message="🏃 Герой успішно втік з бою!"
                )
            else:
                return CombatActionResult(
                    attacker="hero",
                    action=action,
                    damage=0,
                    is_critical=False,
                    is_dodged=False,
                    message="❌ Не вдалося втекти! Бій продовжується."
                )
        
        # Attack or Magic action
        hero_stats_dict = {
            'atk': combat_state.hero_stats.atk,
            'mag': combat_state.hero_stats.mag,
            'crit_chance': combat_state.hero_stats.crit_chance
        }
        
        monster_stats_dict = {
            'dodge': combat_state.monster_stats.dodge
        }
        
        # Check for critical hit
        is_critical = CombatCalculator.check_critical_hit(hero_stats_dict)
        
        # Check for dodge
        is_dodged = CombatCalculator.check_dodge(monster_stats_dict)
        
        if is_dodged:
            return CombatActionResult(
                attacker="hero",
                action=action,
                damage=0,
                is_critical=False,
                is_dodged=True,
                message=f"💨 {combat_state.monster_stats.monster_type if hasattr(combat_state.monster_stats, 'monster_type') else 'Монстр'} ухилився від атаки!"
            )
        
        # Calculate damage
        damage = CombatCalculator.calculate_damage(
            hero_stats_dict, monster_stats_dict, action, is_critical
        )
        
        # Apply defense reduction
        damage = CombatCalculator.calculate_defense_reduction(
            damage, combat_state.monster_defending
        )
        
        # Apply damage
        combat_state.monster_hp = max(0, combat_state.monster_hp - damage)
        
        # Create result message
        action_name = "атакує" if action == CombatAction.ATTACK else "використовує магію"
        crit_text = " 💥КРИТИЧНИЙ УДАР!" if is_critical else ""
        message = f"⚔️ {combat_state.hero_stats.name if hasattr(combat_state.hero_stats, 'name') else 'Герой'} {action_name} і завдає {damage} шкоди{crit_text}"
        
        return CombatActionResult(
            attacker="hero",
            action=action,
            damage=damage,
            is_critical=is_critical,
            is_dodged=False,
            message=message
        )
    
    def execute_monster_action(self, user_id: int) -> Optional[CombatActionResult]:
        """Execute monster's combat action (AI controlled)."""
        if user_id not in self.active_combats:
            return None
        
        combat_state = self.active_combats[user_id]
        
        # Simple AI: 70% attack, 20% magic, 10% defend
        action_weights = [0.7, 0.2, 0.1]
        actions = [CombatAction.ATTACK, CombatAction.MAGIC, CombatAction.DEFEND]
        action = random.choices(actions, weights=action_weights)[0]
        
        if action == CombatAction.DEFEND:
            combat_state.monster_defending = True
            return CombatActionResult(
                attacker="monster",
                action=action,
                damage=0,
                is_critical=False,
                is_dodged=False,
                message=f"🛡️ {combat_state.monster_stats.monster_type if hasattr(combat_state.monster_stats, 'monster_type') else 'Монстр'} захищається!"
            )
        
        # Attack or Magic action
        monster_stats_dict = {
            'atk': combat_state.monster_stats.atk,
            'mag': combat_state.monster_stats.mag,
            'crit_chance': combat_state.monster_stats.crit_chance
        }
        
        hero_stats_dict = {
            'dodge': combat_state.hero_stats.dodge
        }
        
        # Check for critical hit
        is_critical = CombatCalculator.check_critical_hit(monster_stats_dict)
        
        # Check for dodge
        is_dodged = CombatCalculator.check_dodge(hero_stats_dict)
        
        if is_dodged:
            return CombatActionResult(
                attacker="monster",
                action=action,
                damage=0,
                is_critical=False,
                is_dodged=True,
                message=f"💨 {combat_state.hero_stats.name if hasattr(combat_state.hero_stats, 'name') else 'Герой'} ухилився від атаки!"
            )
        
        # Calculate damage
        damage = CombatCalculator.calculate_damage(
            monster_stats_dict, hero_stats_dict, action, is_critical
        )
        
        # Apply defense reduction
        damage = CombatCalculator.calculate_defense_reduction(
            damage, combat_state.hero_defending
        )
        
        # Apply damage
        combat_state.hero_hp = max(0, combat_state.hero_hp - damage)
        
        # Create result message
        action_name = "атакує" if action == CombatAction.ATTACK else "використовує магію"
        crit_text = " 💥КРИТИЧНИЙ УДАР!" if is_critical else ""
        message = f"👹 {combat_state.monster_stats.monster_type if hasattr(combat_state.monster_stats, 'monster_type') else 'Монстр'} {action_name} і завдає {damage} шкоди{crit_text}"
        
        return CombatActionResult(
            attacker="monster",
            action=action,
            damage=damage,
            is_critical=is_critical,
            is_dodged=False,
            message=message
        )
    
    def check_combat_end(self, user_id: int) -> Optional[CombatResult]:
        """Check if combat has ended and return the result."""
        if user_id not in self.active_combats:
            return None
        
        combat_state = self.active_combats[user_id]
        
        if combat_state.hero_hp <= 0:
            del self.active_combats[user_id]
            return CombatResult.MONSTER_WIN
        
        if combat_state.monster_hp <= 0:
            del self.active_combats[user_id]
            return CombatResult.HERO_WIN
        
        return CombatResult.ONGOING
    
    def get_combat_state(self, user_id: int) -> Optional[CombatState]:
        """Get current combat state for a user."""
        return self.active_combats.get(user_id)
    
    def end_combat(self, user_id: int):
        """Force end combat for a user."""
        if user_id in self.active_combats:
            del self.active_combats[user_id]
    
    def format_combat_status(self, combat_state: CombatState) -> str:
        """Format current combat status for display."""
        hero_name = combat_state.hero_stats.name if hasattr(combat_state.hero_stats, 'name') else 'Герой'
        monster_name = combat_state.monster_stats.monster_type if hasattr(combat_state.monster_stats, 'monster_type') else 'Монстр'
        
        # Create HP bars
        hero_hp_percent = (combat_state.hero_hp / combat_state.hero_stats.hp_max) * 100
        monster_hp_percent = (combat_state.monster_hp / combat_state.monster_stats.hp_max) * 100
        
        hero_bar = self._create_hp_bar(hero_hp_percent)
        monster_bar = self._create_hp_bar(monster_hp_percent)
        
        status_text = f"""
⚔️ <b>БІЙ - Хід {combat_state.turn}</b>

❤️ <b>{hero_name}</b>
{hero_bar} {combat_state.hero_hp}/{combat_state.hero_stats.hp_max} HP

👹 <b>{monster_name}</b>
{monster_bar} {combat_state.monster_hp}/{combat_state.monster_stats.hp_max} HP

🛡️ Захист: {'Так' if combat_state.hero_defending else 'Ні'}
"""
        return status_text.strip()
    
    def _create_hp_bar(self, percentage: float, length: int = 10) -> str:
        """Create a visual HP bar."""
        filled = int((percentage / 100) * length)
        empty = length - filled
        
        if percentage > 60:
            color = "🟢"
        elif percentage > 30:
            color = "🟡"
        else:
            color = "🔴"
        
        return color + "█" * filled + "░" * empty
    
    def get_combat_rewards(self, combat_state: CombatState) -> Dict[str, int]:
        """Calculate rewards for winning combat."""
        if combat_state.monster_hp <= 0:
            xp_reward = MonsterCalculator.calculate_experience_reward(combat_state.monster_stats)
            gold_reward = MonsterCalculator.calculate_gold_reward(combat_state.monster_stats)
            
            return {
                'experience': xp_reward,
                'gold': gold_reward
            }
        return {'experience': 0, 'gold': 0}


# Global combat engine instance
combat_engine = CombatEngine()
