# Monster System Documentation

## Overview

The Monster System is a comprehensive RPG monster management system that provides balanced combat encounters for players. The system includes monster classes, stat calculations, and reward systems that integrate seamlessly with the existing hero system.

## Architecture

### Database Models

#### MonsterClass
- `id`: Primary key
- `name`: Monster class name (e.g., "Гоблін", "Дракон")
- `description`: Detailed description of the monster
- `monster_type`: Type of monster ('beast', 'undead', 'demon', 'elemental', 'humanoid')
- `difficulty`: Difficulty level ('easy', 'normal', 'hard', 'boss')
- `base_str`, `base_agi`, `base_int`, `base_vit`, `base_luk`: Base stats
- `stat_growth`: JSON string defining stat growth per level

#### Monster
- `id`: Primary key
- `monster_class_id`: Foreign key to MonsterClass
- `name`: Individual monster name (e.g., "Гоблін-розвідник")
- `level`: Monster level
- `current_hp`: Current hit points
- `location`: Where this monster can be found
- `is_active`: Whether monster is currently spawned
- `created_at`, `last_activity_at`: Timestamps

## Monster Classes

### Easy Monsters (🟢)
- **Гоблін**: Quick humanoid with high agility
- **Вовк**: Fast beast with balanced stats

### Normal Monsters (🟡)
- **Скелет**: Slow but tough undead
- **Орк**: Strong humanoid warrior

### Hard Monsters (🟠)
- **Вогняний Елементаль**: Magical elemental with high intelligence
- **Менший Демон**: Balanced demon with good all-around stats

### Boss Monsters (🔴)
- **Молодий Дракон**: Powerful beast with high stats across the board
- **Ліч**: Magical undead with extremely high intelligence

## Stat System

### Base Stats
Monsters use the same stat system as heroes:
- **STR (Сила)**: Physical attack power
- **AGI (Спритність)**: Critical hit chance and dodge
- **INT (Інтелект)**: Magical attack power
- **VIT (Витривалість)**: Hit points
- **LUK (Удача)**: Critical hit chance bonus

### Derived Stats
- **HP_MAX**: 20 + 4 × VIT
- **ATK**: 2 + STR
- **MAG**: 2 + INT
- **CRIT_CHANCE**: 5% + 0.5 × AGI (capped at 35%)
- **DODGE**: 2% + 0.4 × AGI (capped at 25%)

### Level Scaling
Monsters gain stats based on their level using the `stat_growth` formula:
- Level 1: Base stats only
- Level 2+: Base stats + (stat_growth × (level - 1))

## Reward System

### Experience Rewards
Formula: `(10 + level × 5) × difficulty_multiplier`
- Easy: 1.0x
- Normal: 1.5x
- Hard: 2.0x
- Boss: 3.0x

### Gold Rewards
Formula: `(5 + level × 3) × difficulty_multiplier`
- Easy: 1.0x
- Normal: 1.2x
- Hard: 1.5x
- Boss: 2.0x

## Monster Types

### 🐺 Beast
- Natural creatures and animals
- Examples: Wolves, Dragons, Bears
- Typically high STR and AGI

### 💀 Undead
- Animated corpses and spirits
- Examples: Skeletons, Liches, Zombies
- Typically high VIT and INT

### 👹 Demon
- Infernal creatures from other planes
- Examples: Lesser Demons, Imps, Devils
- Balanced stats with magical abilities

### ⚡ Elemental
- Beings of pure elemental energy
- Examples: Fire Elementals, Ice Spirits, Earth Golems
- Typically high INT and specialized abilities

### 👤 Humanoid
- Human-like creatures with intelligence
- Examples: Goblins, Orcs, Bandits
- Varied stats depending on class

## Integration with Existing Systems

### Hero System Compatibility
- Uses identical stat formulas as heroes
- Balanced for fair combat encounters
- Compatible with existing hero progression

### Quest System Integration
- Monsters can be spawned for quest encounters
- Location-based spawning for area-specific quests
- Difficulty scaling for quest progression

### Town System Integration
- Monsters can be associated with specific locations
- Barracks can show available monster hunts
- Location-based monster spawning

## Usage Examples

### Creating a Monster
```python
# Create a level 5 goblin in the forest
goblin = await create_monster(
    session=session,
    monster_class_id=goblin_class.id,
    name="Гоблін-воїн",
    level=5,
    location="Ліс біля села"
)
```

### Calculating Monster Stats
```python
# Get monster stats for combat
monster_stats = MonsterCalculator.create_monster_stats(monster, monster_class)
print(f"HP: {monster_stats.hp_current}/{monster_stats.hp_max}")
print(f"Attack: {monster_stats.atk}")
```

### Displaying Monster Information
```python
# Format monster for Telegram display
display_text = MonsterCalculator.format_monster_display(
    monster_stats, monster, monster_class
)
```

## Database Functions

### Monster Class Functions
- `create_monster_class()`: Create new monster class
- `get_monster_class_by_id()`: Get class by ID
- `get_monster_class_by_name()`: Get class by name
- `get_all_monster_classes()`: Get all classes
- `get_monster_classes_by_type()`: Filter by monster type
- `get_monster_classes_by_difficulty()`: Filter by difficulty

### Monster Instance Functions
- `create_monster()`: Create new monster instance
- `get_monster_by_id()`: Get monster by ID
- `get_active_monsters()`: Get all active monsters
- `get_monsters_by_location()`: Filter by location
- `get_monsters_by_level_range()`: Filter by level range
- `update_monster()`: Update monster data
- `deactivate_monster()`: Remove from active spawns

## Testing

Run the test suite:
```bash
python test_monsters.py
```

This will:
1. Initialize the database
2. Create all monster classes
3. Test monster creation and stat calculation
4. Test database queries
5. Verify display formatting

## Future Enhancements

1. **Combat System**: Full turn-based combat mechanics
2. **Monster AI**: Different behavior patterns for different monster types
3. **Loot System**: Items and equipment drops from monsters
4. **Monster Spawning**: Dynamic monster generation based on player level
5. **Monster Evolution**: Monsters that grow stronger over time
6. **Group Encounters**: Multiple monsters in single battles
7. **Monster Abilities**: Special attacks and skills unique to each type
8. **Environmental Effects**: Location-based monster modifications
9. **Monster Taming**: Ability to recruit certain monsters as allies
10. **Boss Mechanics**: Special boss fight mechanics and phases
