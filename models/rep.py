"""Reputation utilities shared between gameplay systems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class ReputationTier:
    """Named tier that corresponds to a reputation score interval."""

    code: str
    name: str
    description: str
    min_score: int
    max_score: int | None  # None represents open-ended upper bound


_REPUTATION_TIERS: List[ReputationTier] = [
    ReputationTier(
        code="hostile",
        name="Ворожнеча",
        description="Фракція вороже ставиться до героя і може атакувати першою.",
        min_score=-100,
        max_score=-26,
    ),
    ReputationTier(
        code="wary",
        name="Недовіра",
        description="Фракція насторожено ставиться до героя, пропозиції обмежені.",
        min_score=-25,
        max_score=-1,
    ),
    ReputationTier(
        code="neutral",
        name="Нейтралітет",
        description="Фракція ставиться до героя рівно, без особливих привілеїв.",
        min_score=0,
        max_score=24,
    ),
    ReputationTier(
        code="allied",
        name="Союз",
        description="Герой користується довірою фракції та відкриває додаткові можливості.",
        min_score=25,
        max_score=59,
    ),
    ReputationTier(
        code="champion",
        name="Покровитель",
        description="Фракція вважає героя своїм чемпіоном та пропонує унікальні квести.",
        min_score=60,
        max_score=None,
    ),
]

REPUTATION_MIN: int = _REPUTATION_TIERS[0].min_score
REPUTATION_MAX: int = 100


def clamp_score(score: int) -> int:
    """Clamp reputation score to the supported interval."""
    return max(REPUTATION_MIN, min(REPUTATION_MAX, score))


def resolve_tier(score: int) -> ReputationTier:
    """Return the tier that matches the given score."""
    score = clamp_score(score)
    for tier in _REPUTATION_TIERS:
        upper = REPUTATION_MAX if tier.max_score is None else tier.max_score
        if tier.min_score <= score <= upper:
            return tier
    # Fallback: return highest tier if we did not match due to rounding
    return _REPUTATION_TIERS[-1]


def iter_tiers() -> Iterable[ReputationTier]:
    """Iterate over configured reputation tiers."""
    return _REPUTATION_TIERS


__all__ = [
    "ReputationTier",
    "REPUTATION_MIN",
    "REPUTATION_MAX",
    "clamp_score",
    "resolve_tier",
    "iter_tiers",
]
