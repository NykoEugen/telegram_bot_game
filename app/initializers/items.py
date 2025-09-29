"""Initializer for loading default items into the database."""

import json
from pathlib import Path

from app.database import get_db_session, upsert_item


def _items_file() -> Path:
    """Return path to item definitions."""
    return Path(__file__).resolve().parents[1] / "data" / "items.json"


async def init_items() -> None:
    """Load default items from JSON into the database."""
    path = _items_file()
    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    items = data.get("items", [])
    if not items:
        return

    async for session in get_db_session():
        for item_data in items:
            effect_data = json.dumps(item_data.get("effect", {}), ensure_ascii=False)
            await upsert_item(
                session=session,
                code=item_data["code"],
                name=item_data.get("name", item_data["code"]),
                description=item_data.get("description", ""),
                effect_data=effect_data,
                icon=item_data.get("icon"),
                can_use_in_combat=item_data.get("can_use_in_combat", True),
                can_use_outside_combat=item_data.get("can_use_outside_combat", True),
            )
        break
