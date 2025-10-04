"""Utilities for resolving graph quest node events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import random


@dataclass
class EventResolution:
    """Result of running a node event."""

    event_id: str
    status: str  # success, failure, story
    messages: List[str] = field(default_factory=list)
    damage: int = 0
    rewards: Dict[str, Any] = field(default_factory=dict)
    metrics: List[Tuple[str, int]] = field(default_factory=list)
    require_recovery: bool = False
    story_key: Optional[str] = None


def _hero_attribute(hero_stats, attr: str) -> int:
    if not attr:
        return 0
    attrs = getattr(hero_stats, "attrs", None)
    if isinstance(attrs, dict) and attr in attrs:
        return int(attrs.get(attr, 0))
    value = getattr(hero_stats, attr, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_reward(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    reward: Dict[str, Any] = {}
    if raw.get("items"):
        reward["items"] = list(raw["items"])
    world_flags = raw.get("world_flags")
    if isinstance(world_flags, dict):
        reward["world_flags"] = world_flags
    if raw.get("metric"):
        reward["metric"] = raw["metric"]
    if raw.get("metrics"):
        reward.setdefault("metrics", raw["metrics"])
    return reward


def _collect_metrics(block: Dict[str, Any]) -> List[Tuple[str, int]]:
    metrics: List[Tuple[str, int]] = []
    metric = block.get("metric")
    if isinstance(metric, dict):
        name = metric.get("name")
        if name:
            metrics.append((name, int(metric.get("amount", 1))))
    for entry in block.get("metrics", []) or []:
        if isinstance(entry, dict):
            name = entry.get("name")
            if name:
                metrics.append((name, int(entry.get("amount", 1))))
    return metrics


def _stat_check_event(
    event_id: str,
    event: Dict[str, Any],
    hero_stats,
    rng: random.Random
) -> EventResolution:
    attribute = (event.get("attribute") or "agi").lower()
    difficulty = int(event.get("difficulty", 10))
    dice = int(event.get("dice", 0))
    base_value = _hero_attribute(hero_stats, attribute)
    roll_bonus = rng.randint(1, dice) if dice > 0 else 0
    total = base_value + roll_bonus

    success_block = event.get("success", {}) if isinstance(event.get("success"), dict) else {}
    failure_block = event.get("failure", {}) if isinstance(event.get("failure"), dict) else {}

    success = total >= difficulty
    messages: List[str] = []

    if success:
        text = success_block.get("text") or event.get("success_text")
        if text:
            messages.append(text)
        else:
            messages.append(
                f"✅ Перевірка {attribute.upper()} успішна ({total}/{difficulty})."
            )
        reward = _normalize_reward(success_block.get("reward") or event.get("reward", {}))
        metrics = _collect_metrics(success_block)
        metrics.extend(_collect_metrics(reward))
        return EventResolution(
            event_id=event_id,
            status="success",
            messages=messages,
            rewards=reward,
            metrics=metrics,
        )

    text = failure_block.get("text") or event.get("failure_text")
    if text:
        messages.append(text)
    else:
        messages.append(
            f"⚠️ Перевірка {attribute.upper()} не вдалася ({total}/{difficulty})."
        )
    damage = int(
        failure_block.get("damage")
        or event.get("failure_damage")
        or event.get("damage", 0)
    )
    reward = _normalize_reward(failure_block.get("reward", {}))
    metrics = _collect_metrics(failure_block)
    metrics.extend(_collect_metrics(reward))
    require_recovery = bool(failure_block.get("require_recovery"))

    return EventResolution(
        event_id=event_id,
        status="failure",
        messages=messages,
        damage=damage,
        rewards=reward,
        metrics=metrics,
        require_recovery=require_recovery,
    )


def _puzzle_event(
    event_id: str,
    event: Dict[str, Any],
) -> EventResolution:
    text = event.get("text") or event.get("success_text")
    if not text:
        text = "🧩 Ви розгадуєте загадку та отримуєте підказку."
    reward = _normalize_reward(event.get("reward", {}))
    metrics = _collect_metrics(event)
    metrics.extend(_collect_metrics(reward))
    return EventResolution(
        event_id=event_id,
        status="success",
        messages=[text],
        rewards=reward,
        metrics=metrics,
    )


def _story_event(event_id: str, event: Dict[str, Any]) -> EventResolution:
    text = event.get("text") or "✨ Ви стаєте свідком рідкісної події."
    reward = _normalize_reward(event.get("reward", {}))
    metrics = _collect_metrics(event)
    metrics.extend(_collect_metrics(reward))
    story_key = event.get("story_key") or event_id
    return EventResolution(
        event_id=event_id,
        status="story",
        messages=[text],
        rewards=reward,
        metrics=metrics,
        story_key=story_key,
    )


def resolve_node_events(
    events: Sequence[Dict[str, Any]],
    hero_stats,
    resolved_event_ids: Iterable[str],
    rng: random.Random
) -> List[EventResolution]:
    """Resolve node events, skipping already processed ones."""

    resolved_set = set(str(eid) for eid in resolved_event_ids)
    outcomes: List[EventResolution] = []

    for index, raw_event in enumerate(events):
        if not isinstance(raw_event, dict):
            continue
        event_id = str(raw_event.get("id") or f"event_{index}")
        if event_id in resolved_set and not raw_event.get("repeatable"):
            continue

        event_type = (raw_event.get("type") or "stat_check").lower()

        if event_type in {"trap", "stat_check"}:
            outcome = _stat_check_event(event_id, raw_event, hero_stats, rng)
        elif event_type == "puzzle":
            outcome = _puzzle_event(event_id, raw_event)
        elif event_type == "story_moment":
            outcome = _story_event(event_id, raw_event)
        else:
            # Fallback: treat as flavour story moment
            outcome = EventResolution(
                event_id=event_id,
                status="success",
                messages=[raw_event.get("text") or "Ви просуваєтесь далі."],
            )

        outcomes.append(outcome)

    return outcomes


__all__ = ["EventResolution", "resolve_node_events"]
