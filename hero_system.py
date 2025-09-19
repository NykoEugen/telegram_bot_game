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
    """Predefined hero classes with their stats and growth."""
    
    @staticmethod
    def get_warrior_data() -> Dict[str, Any]:
        """Warrior class data: STR+2, VIT+2 / рівень: +STR, +VIT"""
        return {
            'name': 'Воїн',
            'description': 'Міцний борець, який покладається на силу та витривалість. Відмінний у ближньому бою.',
            'str_bonus': 2,
            'agi_bonus': 0,
            'int_bonus': 0,
            'vit_bonus': 2,
            'luk_bonus': 0,
            'stat_growth': '{"str": 1, "agi": 0, "int": 0, "vit": 1, "luk": 0}'
        }
    
    @staticmethod
    def get_rogue_data() -> Dict[str, Any]:
        """Rogue class data: AGI+2, LUK+1 / рівень: +AGI, +LUK"""
        return {
            'name': 'Розбійник',
            'description': 'Спритний і удачливий воїн. Має високу шанс критичного удару та ухилення.',
            'str_bonus': 0,
            'agi_bonus': 2,
            'int_bonus': 0,
            'vit_bonus': 0,
            'luk_bonus': 1,
            'stat_growth': '{"str": 0, "agi": 1, "int": 0, "vit": 0, "luk": 1}'
        }
    
    @staticmethod
    def get_mage_data() -> Dict[str, Any]:
        """Mage class data: INT+3 / рівень: +INT, +AGI"""
        return {
            'name': 'Маг',
            'description': 'Могутній заклинатель, який використовує магію для атаки. Високий магічний урон.',
            'str_bonus': 0,
            'agi_bonus': 0,
            'int_bonus': 3,
            'vit_bonus': 0,
            'luk_bonus': 0,
            'stat_growth': '{"str": 0, "agi": 1, "int": 1, "vit": 0, "luk": 0}'
        }
    
    @staticmethod
    def get_cleric_data() -> Dict[str, Any]:
        """Cleric class data: INT+1, VIT+2 / рівень: +VIT, +INT"""
        return {
            'name': 'Клірик',
            'description': 'Священний воїн, який поєднує магію з витривалістю. Відмінний підтримкою та захистом.',
            'str_bonus': 0,
            'agi_bonus': 0,
            'int_bonus': 1,
            'vit_bonus': 2,
            'luk_bonus': 0,
            'stat_growth': '{"str": 0, "agi": 0, "int": 1, "vit": 1, "luk": 0}'
        }
    
    @staticmethod
    def get_ranger_data() -> Dict[str, Any]:
        """Ranger class data: STR+1, AGI+2 / рівень: +AGI, +STR"""
        return {
            'name': 'Рейнджер',
            'description': 'Універсальний борець, який поєднує силу та спритність. Добре збалансований клас.',
            'str_bonus': 1,
            'agi_bonus': 2,
            'int_bonus': 0,
            'vit_bonus': 0,
            'luk_bonus': 0,
            'stat_growth': '{"str": 1, "agi": 1, "int": 0, "vit": 0, "luk": 0}'
        }
    
    @staticmethod
    def get_all_classes() -> list[Dict[str, Any]]:
        """Get all hero classes data."""
        return [
            HeroClasses.get_warrior_data(),
            HeroClasses.get_rogue_data(),
            HeroClasses.get_mage_data(),
            HeroClasses.get_cleric_data(),
            HeroClasses.get_ranger_data()
        ]
