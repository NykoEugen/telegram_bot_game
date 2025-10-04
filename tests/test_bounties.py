"""Tests for bounty generation utilities."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.bounties import BountyGenerator


@pytest.mark.parametrize(
    "seed",
    [0, 1, 99999],
)
def test_bounty_generator_deterministic(seed: int) -> None:
    template = SimpleNamespace(
        id=1,
        code="hunt_basic",
        title="Полювання на {target} у {location}",
        description="Знешкодьте {target} поблизу {location}.",
        category="hunt",
        duration_minutes=6,
        data='{"locations": ["Північні поля", "Глухий гай"], "targets": ["зграю гоблінів", "загін мародерів"], "rewards": {"gold": [80, 120], "xp": [100, 140]}}',
        is_active=True,
    )

    gen_a = BountyGenerator(random_seed=seed)
    gen_b = BountyGenerator(random_seed=seed)

    bounty_a = gen_a.generate_bounty(template)
    bounty_b = gen_b.generate_bounty(template)

    assert bounty_a.payload == bounty_b.payload
    assert bounty_a.seed.startswith(template.code)


def test_bounty_payload_structure() -> None:
    template = SimpleNamespace(
        id=2,
        code="escort_basic",
        title="Супровід {target} до {location}",
        description="Забезпечте безпечну подорож до {location}.",
        category="escort",
        duration_minutes=7,
        data='{"locations": ["Форпост"], "targets": ["караван"], "rewards": {"gold": [90, 90], "xp": [120, 120]}, "static_rewards": {"token": 1}, "objectives": ["Захист", "Перевірка"]}',
        is_active=True,
    )

    generator = BountyGenerator(random_seed=123)
    bounty = generator.generate_bounty(template)

    payload = bounty.payload
    assert payload["title"].startswith("Супровід")
    assert payload["rewards"]["gold"] == 90
    assert payload["rewards"]["xp"] == 120
    assert payload["rewards"]["token"] == 1
    assert payload["objectives"] == ["Захист", "Перевірка"]
