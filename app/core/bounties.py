"""Procedural bounty generation utilities."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    ActiveBounty,
    BountyTemplate,
    HeroBountyProgress,
    create_active_bounty,
    get_active_bounty_templates,
    get_current_active_bounties,
)


BOUNTY_DEFAULT_DURATION_MINUTES = 6


@dataclass
class GeneratedBounty:
    """In-memory representation of a generated bounty instance."""

    template: BountyTemplate
    seed: str
    payload: Dict[str, object]
    available_from: datetime
    expires_at: datetime
    tier: str = "standard"

    def as_active_kwargs(self) -> Dict[str, object]:
        return {
            "template_id": self.template.id,
            "seed": self.seed,
            "payload": self.payload,
            "available_from": self.available_from.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "tier": self.tier,
        }


class BountyGenerator:
    """Generates repeatable bounties from templates."""

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self._rng = random.Random(random_seed)

    def _choose_template(self, templates: Sequence[BountyTemplate]) -> Optional[BountyTemplate]:
        active = [template for template in templates if template.is_active]
        if not active:
            return None
        return self._rng.choice(active)

    def _generate_payload(self, template: BountyTemplate, seed: str) -> Dict[str, object]:
        data = json.loads(template.data)

        # Example expansions. Real implementation can branch on template.category.
        locations = data.get("locations", ["Outskirts", "Forest Edge", "Abandoned Camp"])
        targets = data.get("targets", ["Goblin Raiders", "Bandit Scouts", "Stray Elemental"])
        rewards = data.get("rewards", {"gold": [90, 110], "xp": [120, 160]})

        location = self._rng.choice(locations)
        target = self._rng.choice(targets)

        reward_gold_range = rewards.get("gold", [80, 120])
        reward_xp_range = rewards.get("xp", [100, 150])

        reward_gold = self._rng.randint(*sorted(reward_gold_range))
        reward_xp = self._rng.randint(*sorted(reward_xp_range))

        return {
            "title": template.title.format(location=location, target=target),
            "description": data.get("description", "Hunt down the threat and report back.").format(
                location=location,
                target=target,
            ),
            "target": target,
            "location": location,
            "objectives": data.get("objectives", []),
            "rewards": {
                "gold": reward_gold,
                "xp": reward_xp,
                **data.get("static_rewards", {}),
            },
        }

    def generate_bounty(
        self,
        template: BountyTemplate,
        duration_minutes: Optional[int] = None,
        tier: str = "standard"
    ) -> GeneratedBounty:
        seed = f"{template.code}:{self._rng.randint(0, 1_000_000)}"
        now = datetime.now(UTC)
        duration = duration_minutes or template.duration_minutes or BOUNTY_DEFAULT_DURATION_MINUTES
        expires_at = now + timedelta(minutes=duration)

        payload = self._generate_payload(template, seed)

        return GeneratedBounty(
            template=template,
            seed=seed,
            payload=payload,
            available_from=now,
            expires_at=expires_at,
            tier=tier,
        )


async def ensure_active_bounties(
    session: AsyncSession,
    *,
    generator: BountyGenerator,
    desired_count: int = 3,
    category: Optional[str] = None
) -> List[ActiveBounty]:
    """Ensure that a number of active bounties are available.

    Returns the current active bounty records (existing plus newly generated).
    """

    current = await get_current_active_bounties(session)
    if len(current) >= desired_count:
        return current

    templates = await get_active_bounty_templates(session, category)
    while len(current) < desired_count:
        template = generator._choose_template(templates)
        if not template:
            break

        generated = generator.generate_bounty(template)
        active = await create_active_bounty(session, **generated.as_active_kwargs())
        current.append(active)

    return current


async def serialize_active_bounty(bounty: ActiveBounty) -> Dict[str, object]:
    """Return dict representation of an active bounty row."""

    return {
        "id": bounty.id,
        "template_id": bounty.template_id,
        "seed": bounty.seed,
        "tier": bounty.tier,
        "available_from": bounty.available_from,
        "expires_at": bounty.expires_at,
        "payload": json.loads(bounty.payload),
    }
