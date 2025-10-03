"""Static achievement definitions for hero progression."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AchievementDefinition:
    """Immutable description of a single achievement."""

    code: str
    name: str
    description: str
    icon: str
    metric: str
    target_value: int
    order: int = 0


ACHIEVEMENTS: Dict[str, AchievementDefinition] = {
    "boss_slayer_i": AchievementDefinition(
        code="boss_slayer_i",
        name="Перший тріумф",
        description="Переможи боса вперше та доведи свою силу.",
        icon="👑",
        metric="boss_victories",
        target_value=1,
        order=10,
    ),
    "boss_slayer_v": AchievementDefinition(
        code="boss_slayer_v",
        name="Мисливець на босів",
        description="Переможи п'ять босів і принеси спокій землям.",
        icon="🛡️",
        metric="boss_victories",
        target_value=5,
        order=11,
    ),
    "crit_master_i": AchievementDefinition(
        code="crit_master_i",
        name="Майстер критів",
        description="Завдай 100 критичних ударів у боях.",
        icon="💥",
        metric="critical_hits",
        target_value=100,
        order=20,
    ),
    "crit_master_ii": AchievementDefinition(
        code="crit_master_ii",
        name="Грім війни",
        description="Завдай 500 критичних ударів і тряси поле бою.",
        icon="⚡",
        metric="critical_hits",
        target_value=500,
        order=21,
    ),
    "combat_veteran": AchievementDefinition(
        code="combat_veteran",
        name="Ветеран боїв",
        description="Переможи 25 ворогів у будь-яких битвах.",
        icon="⚔️",
        metric="combat_victories",
        target_value=25,
        order=30,
    ),
    "combat_legend": AchievementDefinition(
        code="combat_legend",
        name="Легенда арени",
        description="Отримай 100 перемог у боях та стань легендою.",
        icon="🔥",
        metric="combat_victories",
        target_value=100,
        order=31,
    ),
    "quest_pathfinder": AchievementDefinition(
        code="quest_pathfinder",
        name="Шлях дослідника",
        description="Заверши сюжетний квест до кінця.",
        icon="🗺️",
        metric="quests_completed",
        target_value=1,
        order=40,
    ),
    "graph_conqueror": AchievementDefinition(
        code="graph_conqueror",
        name="Повний маршрут",
        description="Заверши одну гілку граф-квесту на 100%.",
        icon="🌌",
        metric="graph_quests_completed",
        target_value=1,
        order=41,
    ),
    "graph_master": AchievementDefinition(
        code="graph_master",
        name="Майстер маршрутів",
        description="Заверши п'ять граф-квестів, вивчивши всі гілки.",
        icon="🌠",
        metric="graph_quests_completed",
        target_value=5,
        order=42,
    ),
}


def achievements_by_metric(metric: str) -> List[AchievementDefinition]:
    """Return achievements filtered by metric, ordered for progression."""
    items = [ach for ach in ACHIEVEMENTS.values() if ach.metric == metric]
    return sorted(items, key=lambda definition: (definition.order, definition.target_value))


def all_achievements() -> Iterable[AchievementDefinition]:
    """Return iterable with all achievement definitions."""
    return ACHIEVEMENTS.values()
