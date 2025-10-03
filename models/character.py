"""Character progression and talent helper utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

ATTRIBUTE_KEYS: tuple[str, ...] = ("str", "agi", "int")
ATTRIBUTE_POINTS_PER_LEVEL: int = 3
TALENT_POINTS_PER_LEVEL: int = 1
XP_BASE_REQUIREMENT: int = 100
XP_GROWTH_EXPONENT: float = 1.35


@dataclass(frozen=True)
class TalentDefinition:
    """Represents a single talent that can be unlocked by the player."""

    id: str
    name: str
    description: str
    required_level: int
    modifiers: Dict[str, float] = field(default_factory=dict)


TALENT_LIBRARY: Dict[str, TalentDefinition] = {
    "keen_edge": TalentDefinition(
        id="keen_edge",
        name="Гостре Лезо",
        description="Підсилює фізичні атаки на 12% та додає +5% шансу криту.",
        required_level=2,
        modifiers={"atk_pct": 0.12, "crit_chance_flat": 5.0},
    ),
    "arcane_focus": TalentDefinition(
        id="arcane_focus",
        name="Арканічний Фокус",
        description="Посилює магічні атаки на 15% та додає +3% шансу криту.",
        required_level=2,
        modifiers={"mag_pct": 0.15, "crit_chance_flat": 3.0},
    ),
    "battle_hardened": TalentDefinition(
        id="battle_hardened",
        name="Бойове Гарту",
        description="Збільшує максимальне здоров'я на 10%.",
        required_level=3,
        modifiers={"hp_max_pct": 0.10},
    ),
    "quickstep": TalentDefinition(
        id="quickstep",
        name="Легкі Кроки",
        description="Додає +6% ухилення та трохи підсилює атаку.",
        required_level=3,
        modifiers={"dodge_flat": 6.0, "atk_pct": 0.05},
    ),
}


def xp_to_next_level(level: int) -> int:
    """Return the XP required to reach the next level."""
    level = max(1, level)
    requirement = XP_BASE_REQUIREMENT * math.pow(level, XP_GROWTH_EXPONENT)
    return max(50, int(requirement))


def attribute_points_for_level(level: int) -> int:
    """Number of attribute points granted on the given level."""
    return ATTRIBUTE_POINTS_PER_LEVEL


def talent_points_for_level(level: int) -> int:
    """Number of talent points granted on the given level."""
    return TALENT_POINTS_PER_LEVEL


def apply_talent_modifiers(base_stats: Dict[str, float], talents: Iterable[str]) -> Dict[str, float]:
    """Apply passive talent modifiers to a stats dictionary."""
    modified = dict(base_stats)
    for talent_id in talents:
        definition = TALENT_LIBRARY.get(talent_id)
        if not definition:
            continue
        for modifier, value in definition.modifiers.items():
            if modifier.endswith("_pct"):
                stat_name = modifier[:-4]
                modified[stat_name] = modified.get(stat_name, 0.0) * (1.0 + value)
            elif modifier.endswith("_flat"):
                stat_name = modifier[:-5]
                modified[stat_name] = modified.get(stat_name, 0.0) + value
    return modified


def calculate_physical_power(strength: int, agility: int) -> float:
    """Calculate base physical attack power from STR and AGI."""
    return 6.0 + strength * 1.7 + agility * 0.6


def calculate_magical_power(intellect: int, agility: int) -> float:
    """Calculate base magical attack power from INT and AGI."""
    return 6.0 + intellect * 1.9 + agility * 0.3


def get_unlockable_talents(level: int, unlocked: Iterable[str]) -> List[TalentDefinition]:
    """Return talents that can be unlocked at the current level."""
    unlocked_set = set(unlocked)
    candidates: List[TalentDefinition] = []
    for definition in TALENT_LIBRARY.values():
        if definition.id in unlocked_set:
            continue
        if level < definition.required_level:
            continue
        candidates.append(definition)
    return sorted(candidates, key=lambda talent: talent.required_level)


def get_talent_definition(talent_id: str) -> TalentDefinition | None:
    """Return a talent definition by identifier."""
    return TALENT_LIBRARY.get(talent_id)
