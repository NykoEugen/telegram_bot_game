"""
Hero system logic for calculating stats and derived attributes.
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

from database import Hero, HeroClass


@dataclass
class HeroStats:
    """Calculated hero stats with derived attributes."""
    
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
    
    # Experience and level info
    level: int
    experience: int
    xp_to_next: int


class HeroCalculator:
    """Class for calculating hero stats and derived attributes."""
    
    @staticmethod
    def calculate_total_stats(hero: Hero, hero_class: HeroClass) -> Dict[str, int]:
        """Calculate total stats including class bonuses."""
        return {
            'str': hero.base_str + hero_class.str_bonus,
            'agi': hero.base_agi + hero_class.agi_bonus,
            'int': hero.base_int + hero_class.int_bonus,
            'vit': hero.base_vit + hero_class.vit_bonus,
            'luk': hero.base_luk + hero_class.luk_bonus
        }
    
    @staticmethod
    def calculate_derived_stats(hero: Hero, hero_class: HeroClass) -> Dict[str, Any]:
        """Calculate derived stats based on formulas."""
        total_stats = HeroCalculator.calculate_total_stats(hero, hero_class)
        
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
    def calculate_xp_to_next_level(level: int) -> int:
        """Calculate XP needed for next level: XP_to_next = 50 + 25 * level"""
        return 50 + 25 * level
    
    @staticmethod
    def create_hero_stats(hero: Hero, hero_class: HeroClass) -> HeroStats:
        """Create a complete HeroStats object with all calculated values."""
        total_stats = HeroCalculator.calculate_total_stats(hero, hero_class)
        derived_stats = HeroCalculator.calculate_derived_stats(hero, hero_class)
        xp_to_next = HeroCalculator.calculate_xp_to_next_level(hero.level)
        
        return HeroStats(
            str=total_stats['str'],
            agi=total_stats['agi'],
            int=total_stats['int'],
            vit=total_stats['vit'],
            luk=total_stats['luk'],
            hp_max=derived_stats['hp_max'],
            hp_current=hero.current_hp,
            atk=derived_stats['atk'],
            mag=derived_stats['mag'],
            crit_chance=derived_stats['crit_chance'],
            dodge=derived_stats['dodge'],
            level=hero.level,
            experience=hero.experience,
            xp_to_next=xp_to_next
        )
    
    @staticmethod
    def format_stats_display(hero_stats: HeroStats, hero_class: HeroClass) -> str:
        """Format hero stats for display in Telegram."""
        stats_text = f"""
🏆 <b>{hero_stats.name if hasattr(hero_stats, 'name') else 'Герой'}</b>
⚔️ Клас: {hero_class.name}
📊 Рівень: {hero_stats.level}
⭐ Досвід: {hero_stats.experience}/{hero_stats.xp_to_next}

💪 <b>Основні характеристики:</b>
⚡ Сила (STR): {hero_stats.str}
🎯 Спритність (AGI): {hero_stats.agi}
🧠 Інтелект (INT): {hero_stats.int}
❤️ Витривалість (VIT): {hero_stats.vit}
🍀 Удача (LUK): {hero_stats.luk}

⚔️ <b>Бойові характеристики:</b>
❤️ HP: {hero_stats.hp_current}/{hero_stats.hp_max}
🗡️ Атака: {hero_stats.atk}
🔮 Магія: {hero_stats.mag}
💥 Крит: {hero_stats.crit_chance:.1f}%
🛡️ Ухилення: {hero_stats.dodge:.1f}%
"""
        return stats_text.strip()
    
    @staticmethod
    def format_class_info(hero_class: HeroClass) -> str:
        """Format hero class information for display."""
        stat_growth = json.loads(hero_class.stat_growth)
        
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
⚔️ <b>{hero_class.name}</b>

📝 <i>{hero_class.description}</i>

🎯 <b>Стартові бонуси:</b>
• Сила: +{hero_class.str_bonus}
• Спритність: +{hero_class.agi_bonus}
• Інтелект: +{hero_class.int_bonus}
• Витривалість: +{hero_class.vit_bonus}
• Удача: +{hero_class.luk_bonus}

📈 <b>Зростання за рівень:</b>
{growth_text.strip()}
"""
        return class_info.strip()


class HeroClasses:
    """Hero classes loaded from JSON configuration."""
    
    _classes_data = None
    
    @classmethod
    def _load_classes_data(cls) -> list[Dict[str, Any]]:
        """Load hero classes data from JSON file."""
        if cls._classes_data is None:
            import os
            import json
            
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(current_dir, 'data', 'hero_classes.json')
            
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls._classes_data = data['hero_classes']
            except FileNotFoundError:
                raise FileNotFoundError(f"Hero classes JSON file not found at {json_file_path}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in hero classes file: {e}")
        
        return cls._classes_data
    
    @classmethod
    def get_all_classes(cls) -> list[Dict[str, Any]]:
        """Get all hero classes data from JSON file."""
        classes_data = cls._load_classes_data()
        
        # Convert stat_growth dict to JSON string for compatibility
        for class_data in classes_data:
            if isinstance(class_data['stat_growth'], dict):
                class_data['stat_growth'] = json.dumps(class_data['stat_growth'])
        
        return classes_data
    
    @classmethod
    def get_class_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get hero class data by name."""
        classes_data = cls._load_classes_data()
        
        for class_data in classes_data:
            if class_data['name'] == name:
                # Convert stat_growth dict to JSON string for compatibility
                if isinstance(class_data['stat_growth'], dict):
                    class_data['stat_growth'] = json.dumps(class_data['stat_growth'])
                return class_data
        
        return None
