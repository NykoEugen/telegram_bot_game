"""Lightweight faction catalog used for reputation and quest requirements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class FactionDefinition:
    """Immutable description of a world faction."""

    code: str
    name: str
    description: str
    icon: str = "🛡️"


_FACTION_REGISTRY: Dict[str, FactionDefinition] = {
    "mages_guild": FactionDefinition(
        code="mages_guild",
        name="Орден Архімагів",
        description="Стародавній орден, що дбає про баланс магії у світі.",
        icon="🔮",
    ),
    "hunters_lodge": FactionDefinition(
        code="hunters_lodge",
        name="Мисливська Ліга",
        description="Братство авантюристів, що відстежують монстрів та небезпечних звірів.",
        icon="🏹",
    ),
    "shadow_court": FactionDefinition(
        code="shadow_court",
        name="Тіньовий Двір",
        description="Таємна мережа шпигунів та інформаторів, які шукають вигоду у будь-якій ситуації.",
        icon="🕶️",
    ),
}


def all_factions() -> List[FactionDefinition]:
    """Return every registered faction definition."""
    return list(_FACTION_REGISTRY.values())


def iter_factions() -> Iterable[FactionDefinition]:
    """Iterate over all factions without copying the registry."""
    return _FACTION_REGISTRY.values()


def get_faction(code: str) -> FactionDefinition | None:
    """Return a single faction definition by code."""
    return _FACTION_REGISTRY.get(code)


def ensure_faction(code: str) -> FactionDefinition:
    """Return faction definition or raise a helpful error."""
    faction = get_faction(code)
    if not faction:
        raise ValueError(f"Unknown faction code: {code}")
    return faction


__all__ = [
    "FactionDefinition",
    "all_factions",
    "iter_factions",
    "get_faction",
    "ensure_faction",
]
