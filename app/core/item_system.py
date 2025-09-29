"""Core logic for item effects and inventory interactions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.database import Item as ItemModel


class ItemEffectType(str, Enum):
    """Supported item effect categories."""

    HEAL = "heal"
    CLEANSE = "cleanse"
    UNKNOWN = "unknown"


@dataclass
class ItemEffect:
    """Structured representation of an item's effect payload."""

    effect_type: ItemEffectType
    heal_amount: int = 0
    heal_percent: float = 0.0
    remove_effects: List[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Optional[Dict]) -> "ItemEffect":
        """Create effect description from raw JSON data."""
        raw = raw or {}
        effect_type = ItemEffectType(raw.get("type", ItemEffectType.UNKNOWN))

        return cls(
            effect_type=effect_type,
            heal_amount=int(raw.get("heal_amount", 0)),
            heal_percent=float(raw.get("heal_percent", 0.0)),
            remove_effects=list(raw.get("remove_effects", [])),
        )


@dataclass
class InventoryItemDefinition:
    """Domain representation of an item definition."""

    id: int
    code: str
    name: str
    description: str
    icon: Optional[str]
    can_use_in_combat: bool
    can_use_outside_combat: bool
    effect: ItemEffect

    @property
    def label(self) -> str:
        """Human readable label with fallback icon."""
        prefix = self.icon or "🎒"
        return f"{prefix} {self.name}"


@dataclass
class ItemUseOutcome:
    """Result information after applying an item effect."""

    description: str
    hp_restored: int = 0
    new_hp: Optional[int] = None

    def as_log_entry(self, item_label: str) -> str:
        """Format outcome for combat log."""
        return f"{item_label}: {self.description}"


class ItemEngine:
    """Utility helpers for parsing and applying item effects."""

    @staticmethod
    def parse_model(item: "ItemModel") -> InventoryItemDefinition:
        effect_payload = {}
        if item.effect_data:
            try:
                effect_payload = json.loads(item.effect_data)
            except json.JSONDecodeError:
                effect_payload = {}

        return InventoryItemDefinition(
            id=item.id,
            code=item.code,
            name=item.name,
            description=item.description,
            icon=item.icon,
            can_use_in_combat=item.can_use_in_combat,
            can_use_outside_combat=item.can_use_outside_combat,
            effect=ItemEffect.from_raw(effect_payload),
        )

    @staticmethod
    def apply_effect(
        definition: InventoryItemDefinition,
        *,
        hp_current: int,
        hp_max: int,
    ) -> ItemUseOutcome:
        """Apply the item's effect to supplied HP values."""
        effect = definition.effect

        if effect.effect_type == ItemEffectType.HEAL:
            return ItemEngine._apply_heal(effect, definition, hp_current, hp_max)
        if effect.effect_type == ItemEffectType.CLEANSE:
            return ItemUseOutcome(
                description="Негативні ефекти знято.",
                hp_restored=0,
                new_hp=hp_current,
            )

        return ItemUseOutcome(
            description="З предметом нічого не сталося...",
            hp_restored=0,
            new_hp=hp_current,
        )

    @staticmethod
    def _apply_heal(
        effect: ItemEffect,
        definition: InventoryItemDefinition,
        hp_current: int,
        hp_max: int,
    ) -> ItemUseOutcome:
        heal_from_percent = int(hp_max * max(effect.heal_percent, 0.0))
        base_heal = max(effect.heal_amount, 0)
        total_heal = base_heal + heal_from_percent

        if total_heal <= 0:
            total_heal = max(1, base_heal)

        new_hp = min(hp_max, hp_current + total_heal)
        restored = max(0, new_hp - hp_current)

        if restored == 0:
            return ItemUseOutcome(
                description="HP вже на максимумі.",
                hp_restored=0,
                new_hp=hp_current,
            )

        return ItemUseOutcome(
            description=f"Відновлено {restored} HP.",
            hp_restored=restored,
            new_hp=new_hp,
        )
