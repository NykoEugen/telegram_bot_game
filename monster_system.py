"""
Monster system logic for calculating stats and derived attributes.
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

from database import Monster, MonsterClass


@dataclass
class MonsterStats:
    """Calculated monster stats with derived attributes."""
    
    # Base stats
    str: int
    agi: int
    int: int
    vit: int
    luk: int
    
    # Derived stats
    hp_max: int
    hp_current: int
    atk: int
    mag: int
    crit_chance: float
    dodge: float
    
    # Monster info
    level: int
    monster_type: str
    difficulty: str


class MonsterCalculator:
    """Class for calculating monster stats and derived attributes."""
    
    @staticmethod
    def calculate_total_stats(monster: Monster, monster_class: MonsterClass) -> Dict[str, int]:
        """Calculate total stats including level-based growth."""
        import json
        stat_growth = json.loads(monster_class.stat_growth)
        
        # Calculate stats with level-based growth
        level_bonus = monster.level - 1  # Level 1 has no bonus
        
        return {
            'str': monster_class.base_str + (stat_growth.get('str', 0) * level_bonus),
            'agi': monster_class.base_agi + (stat_growth.get('agi', 0) * level_bonus),
            'int': monster_class.base_int + (stat_growth.get('int', 0) * level_bonus),
            'vit': monster_class.base_vit + (stat_growth.get('vit', 0) * level_bonus),
            'luk': monster_class.base_luk + (stat_growth.get('luk', 0) * level_bonus)
        }
    
    @staticmethod
    def calculate_derived_stats(monster: Monster, monster_class: MonsterClass) -> Dict[str, Any]:
        """Calculate derived stats based on formulas (same as heroes)."""
        total_stats = MonsterCalculator.calculate_total_stats(monster, monster_class)
        
        # HP_MAX = 20 + 4*VIT
        hp_max = 20 + 4 * total_stats['vit']
        
        # ATK = 2 + STR
        atk = 2 + total_stats['str']
        
        # MAG = 2 + INT
        mag = 2 + total_stats['int']
        
        # CRIT_CHANCE = 5% + 0.5*AGI (cap 35%)
        crit_chance = min(35.0, 5.0 + 0.5 * total_stats['agi'])
        
        # DODGE = 2% + 0.4*AGI (cap 25%)
        dodge = min(25.0, 2.0 + 0.4 * total_stats['agi'])
        
        return {
            'hp_max': hp_max,
            'atk': atk,
            'mag': mag,
            'crit_chance': crit_chance,
            'dodge': dodge
        }
    
    @staticmethod
    def create_monster_stats(monster: Monster, monster_class: MonsterClass) -> MonsterStats:
        """Create a complete MonsterStats object with all calculated values."""
        total_stats = MonsterCalculator.calculate_total_stats(monster, monster_class)
        derived_stats = MonsterCalculator.calculate_derived_stats(monster, monster_class)
        
        return MonsterStats(
            str=total_stats['str'],
            agi=total_stats['agi'],
            int=total_stats['int'],
            vit=total_stats['vit'],
            luk=total_stats['luk'],
            hp_max=derived_stats['hp_max'],
            hp_current=monster.current_hp,
            atk=derived_stats['atk'],
            mag=derived_stats['mag'],
            crit_chance=derived_stats['crit_chance'],
            dodge=derived_stats['dodge'],
            level=monster.level,
            monster_type=monster_class.monster_type,
            difficulty=monster_class.difficulty
        )
    
    @staticmethod
    def format_monster_display(monster_stats: MonsterStats, monster: Monster, monster_class: MonsterClass) -> str:
        """Format monster stats for display in Telegram."""
        # Difficulty emoji mapping
        difficulty_emoji = {
            'easy': '🟢',
            'normal': '🟡', 
            'hard': '🟠',
            'boss': '🔴'
        }
        
        # Monster type emoji mapping
        type_emoji = {
            'beast': '🐺',
            'undead': '💀',
            'demon': '👹',
            'elemental': '⚡',
            'humanoid': '👤'
        }
        
        difficulty_icon = difficulty_emoji.get(monster_stats.difficulty, '⚪')
        type_icon = type_emoji.get(monster_stats.monster_type, '❓')
        
        stats_text = f"""
{type_icon} <b>{monster.name}</b> {difficulty_icon}
📊 Рівень: {monster_stats.level}
🏷️ Тип: {monster_class.name}
📝 <i>{monster_class.description}</i>

💪 <b>Основні характеристики:</b>
⚡ Сила (STR): {monster_stats.str}
🎯 Спритність (AGI): {monster_stats.agi}
🧠 Інтелект (INT): {monster_stats.int}
❤️ Витривалість (VIT): {monster_stats.vit}
🍀 Удача (LUK): {monster_stats.luk}

⚔️ <b>Бойові характеристики:</b>
❤️ HP: {monster_stats.hp_current}/{monster_stats.hp_max}
🗡️ Атака: {monster_stats.atk}
🔮 Магія: {monster_stats.mag}
💥 Крит: {monster_stats.crit_chance:.1f}%
🛡️ Ухилення: {monster_stats.dodge:.1f}%
"""
        return stats_text.strip()
    
    @staticmethod
    def format_monster_class_info(monster_class: MonsterClass) -> str:
        """Format monster class information for display."""
        import json
        stat_growth = json.loads(monster_class.stat_growth)
        
        # Difficulty emoji mapping
        difficulty_emoji = {
            'easy': '🟢 Легкий',
            'normal': '🟡 Нормальний', 
            'hard': '🟠 Важкий',
            'boss': '🔴 Бос'
        }
        
        # Monster type emoji mapping
        type_emoji = {
            'beast': '🐺 Звір',
            'undead': '💀 Нежить',
            'demon': '👹 Демон',
            'elemental': '⚡ Елементаль',
            'humanoid': '👤 Гуманоїд'
        }
        
        difficulty_text = difficulty_emoji.get(monster_class.difficulty, '⚪ Невідомо')
        type_text = type_emoji.get(monster_class.monster_type, '❓ Невідомо')
        
        growth_text = ""
        for stat, growth in stat_growth.items():
            if growth > 0:
                stat_names = {
                    'str': 'Сила',
                    'agi': 'Спритність', 
                    'int': 'Інтелект',
                    'vit': 'Витривалість',
                    'luk': 'Удача'
                }
                growth_text += f"• {stat_names.get(stat, stat)}: +{growth}\n"
        
        if not growth_text:
            growth_text = "• Немає зростання характеристик"
        
        class_info = f"""
👹 <b>{monster_class.name}</b>

📝 <i>{monster_class.description}</i>

🏷️ <b>Інформація:</b>
• Тип: {type_text}
• Складність: {difficulty_text}

💪 <b>Базові характеристики:</b>
• Сила: {monster_class.base_str}
• Спритність: {monster_class.base_agi}
• Інтелект: {monster_class.base_int}
• Витривалість: {monster_class.base_vit}
• Удача: {monster_class.base_luk}

📈 <b>Зростання за рівень:</b>
{growth_text.strip()}
"""
        return class_info.strip()
    
    @staticmethod
    def calculate_experience_reward(monster_stats: MonsterStats) -> int:
        """Calculate experience reward for defeating this monster."""
        # Base XP formula: 10 + (level * 5) + difficulty bonus
        base_xp = 10 + (monster_stats.level * 5)
        
        difficulty_multiplier = {
            'easy': 1.0,
            'normal': 1.5,
            'hard': 2.0,
            'boss': 3.0
        }
        
        multiplier = difficulty_multiplier.get(monster_stats.difficulty, 1.0)
        return int(base_xp * multiplier)
    
    @staticmethod
    def calculate_gold_reward(monster_stats: MonsterStats) -> int:
        """Calculate gold reward for defeating this monster."""
        # Base gold formula: 5 + (level * 3) + difficulty bonus
        base_gold = 5 + (monster_stats.level * 3)
        
        difficulty_multiplier = {
            'easy': 1.0,
            'normal': 1.2,
            'hard': 1.5,
            'boss': 2.0
        }
        
        multiplier = difficulty_multiplier.get(monster_stats.difficulty, 1.0)
        return int(base_gold * multiplier)


class MonsterClasses:
    """Predefined monster classes with their stats and growth."""
    
    @staticmethod
    def get_goblin_data() -> Dict[str, Any]:
        """Goblin class data: Easy humanoid monster."""
        return {
            'name': 'Гоблін',
            'description': 'Невеликий гуманоїдний монстр. Слабкий, але швидкий і спритний.',
            'monster_type': 'humanoid',
            'difficulty': 'easy',
            'base_str': 4,
            'base_agi': 7,
            'base_int': 3,
            'base_vit': 5,
            'base_luk': 6,
            'stat_growth': '{"str": 0, "agi": 1, "int": 0, "vit": 0, "luk": 0}'
        }
    
    @staticmethod
    def get_wolf_data() -> Dict[str, Any]:
        """Wolf class data: Easy beast monster."""
        return {
            'name': 'Вовк',
            'description': 'Дикий хижак з гострими зубами та кігтями. Швидкий і агресивний.',
            'monster_type': 'beast',
            'difficulty': 'easy',
            'base_str': 6,
            'base_agi': 8,
            'base_int': 2,
            'base_vit': 6,
            'base_luk': 3,
            'stat_growth': '{"str": 1, "agi": 1, "int": 0, "vit": 0, "luk": 0}'
        }
    
    @staticmethod
    def get_skeleton_data() -> Dict[str, Any]:
        """Skeleton class data: Normal undead monster."""
        return {
            'name': 'Скелет',
            'description': 'Нежить, що складається з кісток. Повільний, але міцний.',
            'monster_type': 'undead',
            'difficulty': 'normal',
            'base_str': 7,
            'base_agi': 3,
            'base_int': 4,
            'base_vit': 8,
            'base_luk': 2,
            'stat_growth': '{"str": 1, "agi": 0, "int": 0, "vit": 1, "luk": 0}'
        }
    
    @staticmethod
    def get_orc_data() -> Dict[str, Any]:
        """Orc class data: Normal humanoid monster."""
        return {
            'name': 'Орк',
            'description': 'Великий гуманоїдний воїн. Сильний і витривалий, але повільний.',
            'monster_type': 'humanoid',
            'difficulty': 'normal',
            'base_str': 9,
            'base_agi': 4,
            'base_int': 3,
            'base_vit': 8,
            'base_luk': 1,
            'stat_growth': '{"str": 1, "agi": 0, "int": 0, "vit": 1, "luk": 0}'
        }
    
    @staticmethod
    def get_fire_elemental_data() -> Dict[str, Any]:
        """Fire Elemental class data: Hard elemental monster."""
        return {
            'name': 'Вогняний Елементаль',
            'description': 'Жива сутність з чистого вогню. Використовує магію для атаки.',
            'monster_type': 'elemental',
            'difficulty': 'hard',
            'base_str': 5,
            'base_agi': 6,
            'base_int': 10,
            'base_vit': 7,
            'base_luk': 4,
            'stat_growth': '{"str": 0, "agi": 0, "int": 2, "vit": 1, "luk": 0}'
        }
    
    @staticmethod
    def get_demon_data() -> Dict[str, Any]:
        """Demon class data: Hard demon monster."""
        return {
            'name': 'Менший Демон',
            'description': 'Демонічна сутність з пекла. Поєднує фізичну силу з магією.',
            'monster_type': 'demon',
            'difficulty': 'hard',
            'base_str': 8,
            'base_agi': 7,
            'base_int': 8,
            'base_vit': 9,
            'base_luk': 5,
            'stat_growth': '{"str": 1, "agi": 1, "int": 1, "vit": 1, "luk": 0}'
        }
    
    @staticmethod
    def get_dragon_data() -> Dict[str, Any]:
        """Dragon class data: Boss monster."""
        return {
            'name': 'Молодий Дракон',
            'description': 'Могутній дракон, що поєднує фізичну силу, магію та витривалість.',
            'monster_type': 'beast',
            'difficulty': 'boss',
            'base_str': 12,
            'base_agi': 8,
            'base_int': 10,
            'base_vit': 15,
            'base_luk': 6,
            'stat_growth': '{"str": 2, "agi": 1, "int": 1, "vit": 2, "luk": 1}'
        }
    
    @staticmethod
    def get_lich_data() -> Dict[str, Any]:
        """Lich class data: Boss undead monster."""
        return {
            'name': 'Ліч',
            'description': 'Могутній некромант, що поєднує магію з незнищенністю нежиті.',
            'monster_type': 'undead',
            'difficulty': 'boss',
            'base_str': 6,
            'base_agi': 5,
            'base_int': 15,
            'base_vit': 12,
            'base_luk': 8,
            'stat_growth': '{"str": 0, "agi": 0, "int": 3, "vit": 2, "luk": 1}'
        }
    
    @staticmethod
    def get_all_classes() -> list[Dict[str, Any]]:
        """Get all monster classes data."""
        return [
            MonsterClasses.get_goblin_data(),
            MonsterClasses.get_wolf_data(),
            MonsterClasses.get_skeleton_data(),
            MonsterClasses.get_orc_data(),
            MonsterClasses.get_fire_elemental_data(),
            MonsterClasses.get_demon_data(),
            MonsterClasses.get_dragon_data(),
            MonsterClasses.get_lich_data()
        ]
