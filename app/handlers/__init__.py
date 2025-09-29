"""Aiogram handler registration."""
from aiogram import Dispatcher

from .common import router as common_router
from .combat import router as combat_router
from .graph_quest import register_graph_quest_handlers
from .hero import register_hero_handlers
from .quest import register_quest_handlers
from .town import register_town_handlers
from .encounter import register_encounter_handlers
from .inventory import router as inventory_router


def register_handlers(dp: Dispatcher) -> None:
    """Attach all routers and FSM handlers to the dispatcher."""
    register_hero_handlers(dp)
    dp.include_router(common_router)
    dp.include_router(combat_router)
    register_encounter_handlers(dp)
    dp.include_router(inventory_router)
    register_quest_handlers(dp)
    register_graph_quest_handlers(dp)
    register_town_handlers(dp)
