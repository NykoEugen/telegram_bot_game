"""Initializer for bounty templates."""

import asyncio
import json
import logging
from pathlib import Path

from app.database import AsyncSessionLocal, create_bounty_template

logger = logging.getLogger(__name__)


TEMPLATE_FILE_CANDIDATES = (
    Path("app/data/bounties.json"),
    Path("data/bounties.json"),
)


def _load_templates() -> list[dict]:
    for candidate in TEMPLATE_FILE_CANDIDATES:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle).get("templates", [])
    raise FileNotFoundError("Не знайдено файл конфігурації винагород (bounties.json)")


async def create_bounty_templates() -> None:
    templates = _load_templates()
    async with AsyncSessionLocal() as session:
        for raw in templates:
            try:
                await create_bounty_template(
                    session=session,
                    code=raw["code"],
                    title=raw["title"],
                    description=raw.get("description", ""),
                    category=raw.get("category", "hunt"),
                    duration_minutes=int(raw.get("duration_minutes", 6)),
                    data=raw.get("data", {}),
                    is_active=raw.get("is_active", True),
                )
                logger.info("Created bounty template %s", raw["code"])
            except Exception as exc:  # pragma: no cover
                logger.error("Failed to create bounty template %s: %s", raw.get("code"), exc)
                raise


async def main():
    await create_bounty_templates()


if __name__ == "__main__":
    asyncio.run(main())

