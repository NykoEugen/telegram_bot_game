"""Unit tests for quest requirement evaluation helpers."""

import pytest

from app.core.quest_requirements import check_quest_requirements

@pytest.mark.asyncio
async def test_requirements_fail_without_hero_for_reputation():
    result = await check_quest_requirements(
        session=None,
        quest_id=7,
        user_id=42,
        hero_id=None,
        requirements={'rep': {'mages_guild': 10}},
    )
    assert not result.met
    assert any('героя' in reason.lower() for reason in result.missing_reasons)


@pytest.mark.asyncio
async def test_requirements_detect_missing_completed_quests(monkeypatch):
    async def fake_load_completed(session, user_id):
        return {1, 2}

    async def fake_format_missing(session, missing):
        return [f"Потрібно завершити {qid}" for qid in missing]

    monkeypatch.setattr(
        'app.core.quest_requirements._load_completed_quests',
        fake_load_completed,
    )
    monkeypatch.setattr(
        'app.core.quest_requirements._format_missing_quests',
        fake_format_missing,
    )

    result = await check_quest_requirements(
        session=None,
        quest_id=5,
        user_id=101,
        hero_id=11,
        requirements={'quests_completed': [1, 3]},
    )

    assert not result.met
    assert result.missing_reasons == ["Потрібно завершити 3"]


@pytest.mark.asyncio
async def test_requirements_world_flags(monkeypatch):
    async def fake_get_flags(session, hero_id):
        return {'dragon_saga.path': 'redemption'}

    monkeypatch.setattr(
        'app.core.quest_requirements.get_hero_world_flags',
        fake_get_flags,
    )

    result = await check_quest_requirements(
        session=None,
        quest_id=9,
        user_id=7,
        hero_id=11,
        requirements={'world_flags': {'has': {'dragon_saga.path': 'redemption'}}},
    )

    assert result.met


@pytest.mark.asyncio
async def test_requirements_world_flags_missing(monkeypatch):
    async def fake_get_flags(session, hero_id):
        return {'dragon_saga.path': 'slayer'}

    monkeypatch.setattr(
        'app.core.quest_requirements.get_hero_world_flags',
        fake_get_flags,
    )

    result = await check_quest_requirements(
        session=None,
        quest_id=10,
        user_id=8,
        hero_id=12,
        requirements={'world_flags': {
            'has': {'dragon_saga.path': 'redemption'},
            'missing': ['dragon_saga.slayer']
        }},
    )

    assert not result.met
    assert any('dragon_saga.path' in reason for reason in result.missing_reasons)
