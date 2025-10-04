"""Unit tests for node event resolution logic."""

from __future__ import annotations

from types import SimpleNamespace
import random

from app.core.node_events import resolve_node_events


def make_stats(str_value: int = 10, agi_value: int = 10, int_value: int = 10):
    return SimpleNamespace(attrs={"str": str_value, "agi": agi_value, "int": int_value})


def test_stat_check_success():
    events = [
        {
            "id": "agility_test",
            "type": "stat_check",
            "attribute": "agi",
            "difficulty": 8,
            "success": {"text": "Ви уникаєте пастки."},
            "failure": {"text": "Отримано ушкодження", "damage": 5},
        }
    ]

    outcomes = resolve_node_events(events, make_stats(agi_value=12), set(), random.Random(1))
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == "success"
    assert outcome.damage == 0
    assert "Ви уникаєте" in outcome.messages[0]


def test_stat_check_failure_deals_damage():
    events = [
        {
            "id": "strength_test",
            "type": "trap",
            "attribute": "str",
            "difficulty": 18,
            "failure": {
                "text": "Камінь падає на вас.",
                "damage": 9,
                "require_recovery": True
            }
        }
    ]

    outcomes = resolve_node_events(events, make_stats(str_value=10), set(), random.Random(2))
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == "failure"
    assert outcome.damage == 9
    assert outcome.require_recovery is True


def test_story_moment_sets_story_key_and_metrics():
    events = [
        {
            "id": "rare_story",
            "type": "story_moment",
            "text": "Ви чуєте шепіт древнього духа.",
            "reward": {
                "world_flags": {"set": {"story.unique": True}},
                "metrics": [{"name": "story_moments", "amount": 2}]
            }
        }
    ]

    outcomes = resolve_node_events(events, make_stats(), set(), random.Random(3))
    assert outcomes[0].status == "story"
    assert outcomes[0].story_key == "rare_story"
    assert outcomes[0].metrics == [("story_moments", 2)]
    assert outcomes[0].rewards["world_flags"]["set"]["story.unique"] is True


def test_repeatable_event_skips_when_already_resolved():
    events = [
        {
            "id": "simple_trap",
            "type": "stat_check",
            "attribute": "agi",
            "difficulty": 5,
        }
    ]

    outcomes = resolve_node_events(events, make_stats(), {"simple_trap"}, random.Random(4))
    assert not outcomes

    outcomes_repeatable = resolve_node_events(
        [{**events[0], "repeatable": True}],
        make_stats(),
        {"simple_trap"},
        random.Random(4)
    )
    assert len(outcomes_repeatable) == 1
