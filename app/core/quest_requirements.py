"""Helpers for evaluating quest prerequisites such as completion and reputation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_completed_graph_quest_ids,
    get_completed_quest_ids,
    get_hero_reputation_map,
    get_hero_world_flags,
    get_quest_requirements,
)
from models.faction import ensure_faction


@dataclass(frozen=True)
class RequirementCheckResult:
    """Aggregated result of checking quest requirements for a user."""

    quest_id: int
    requirements: Dict
    met: bool
    missing_reasons: List[str]

    @property
    def has_requirements(self) -> bool:
        return bool(self.requirements)


async def _load_completed_quests(session: AsyncSession, user_id: int) -> set[int]:
    """Return union of completed quest identifiers for both quest systems."""
    completed = await get_completed_quest_ids(session, user_id)
    completed |= await get_completed_graph_quest_ids(session, user_id)
    return completed


async def _format_missing_quests(
    session: AsyncSession,
    missing_ids: Iterable[int]
) -> List[str]:
    if not missing_ids:
        return []

    missing_ids = list({int(qid) for qid in missing_ids})
    if not missing_ids:
        return []

    from sqlalchemy import select
    from app.database import Quest  # Local import to avoid circular dependency at module import

    result = await session.execute(select(Quest).where(Quest.id.in_(missing_ids)))
    quests_by_id = {quest.id: quest for quest in result.scalars().all()}

    reasons: List[str] = []
    for quest_id in missing_ids:
        quest = quests_by_id.get(quest_id)
        if quest:
            reasons.append(f"Завершіть квест '{quest.title}' (ID {quest_id}).")
        else:
            reasons.append(f"Завершіть квест ID {quest_id}.")
    return reasons


async def check_quest_requirements(
    session: AsyncSession,
    quest_id: int,
    user_id: int,
    hero_id: Optional[int] = None,
    requirements: Optional[Dict] = None
) -> RequirementCheckResult:
    """Evaluate whether the user meets quest requirements.

    Args:
        session: active DB session
        quest_id: quest identifier
        user_id: Telegram user identifier
        hero_id: hero identifier if available
        requirements: raw requirements dictionary
    """

    requirements = requirements or await get_quest_requirements(session, quest_id)
    missing: List[str] = []

    quests_required = requirements.get('quests_completed') if isinstance(requirements, dict) else None
    if quests_required:
        completed = await _load_completed_quests(session, user_id)
        remaining = [qid for qid in quests_required if qid not in completed]
        missing.extend(await _format_missing_quests(session, remaining))

    rep_required = requirements.get('rep') if isinstance(requirements, dict) else None
    if rep_required:
        if hero_id is None:
            missing.append("Створіть героя, щоб накопичувати репутацію фракцій.")
        else:
            hero_rep = await get_hero_reputation_map(session, hero_id)
            for faction_code, min_score in rep_required.items():
                current = hero_rep.get(faction_code, 0)
                if current < min_score:
                    try:
                        faction = ensure_faction(faction_code)
                        reasons = f"{faction.icon} {faction.name}: репутація {current}/{min_score}."
                    except ValueError:
                        reasons = f"Фракція '{faction_code}': репутація {current}/{min_score}."
                    missing.append(reasons)

    flag_required = requirements.get('world_flags') if isinstance(requirements, dict) else None
    if flag_required:
        if hero_id is None:
            missing.append("Створіть героя, щоб формувати історію світу.")
        else:
            hero_flags = await get_hero_world_flags(session, hero_id)
            required_flags = flag_required.get('has') if isinstance(flag_required, dict) else None
            if isinstance(required_flags, dict):
                for key, expected in required_flags.items():
                    if hero_flags.get(key) != expected:
                        missing.append(f"Потрібен світовий прапорець '{key}' = {expected}.")

            missing_flags = flag_required.get('missing') if isinstance(flag_required, dict) else None
            if missing_flags:
                for key in missing_flags:
                    if key in hero_flags:
                        missing.append(f"Прапорець '{key}' має бути відсутній.")

    return RequirementCheckResult(
        quest_id=quest_id,
        requirements=requirements if isinstance(requirements, dict) else {},
        met=not missing,
        missing_reasons=missing,
    )


async def batch_check_quest_requirements(
    session: AsyncSession,
    quest_ids: Iterable[int],
    user_id: int,
    hero_id: Optional[int] = None,
    requirements_map: Optional[Dict[int, Dict]] = None
) -> Dict[int, RequirementCheckResult]:
    """Evaluate requirements for multiple quests in one go."""

    quest_ids = list({int(qid) for qid in quest_ids})
    if not quest_ids:
        return {}

    requirements_map = requirements_map or {}
    results: Dict[int, RequirementCheckResult] = {}

    for quest_id in quest_ids:
        requirements = requirements_map.get(quest_id)
        results[quest_id] = await check_quest_requirements(
            session=session,
            quest_id=quest_id,
            user_id=user_id,
            hero_id=hero_id,
            requirements=requirements,
        )

    return results


__all__ = [
    "RequirementCheckResult",
    "check_quest_requirements",
    "batch_check_quest_requirements",
]
