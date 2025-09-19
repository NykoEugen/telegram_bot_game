"""
Initialize hero classes in the database from JSON configuration.
"""

import logging
from database import get_db_session, create_hero_class, get_all_hero_classes
from hero_system import HeroClasses

logger = logging.getLogger(__name__)


async def init_hero_classes():
    """Initialize all hero classes in the database from JSON configuration."""
    async for session in get_db_session():
        try:
            # Check if classes already exist
            existing_classes = await get_all_hero_classes(session)
            if existing_classes:
                logger.info(f"Hero classes already exist: {[c.name for c in existing_classes]}")
                return existing_classes
            
            # Load and create all hero classes from JSON
            classes_data = HeroClasses.get_all_classes()
            created_classes = []
            
            for class_data in classes_data:
                hero_class = await create_hero_class(
                    session=session,
                    name=class_data['name'],
                    description=class_data['description'],
                    str_bonus=class_data['str_bonus'],
                    agi_bonus=class_data['agi_bonus'],
                    int_bonus=class_data['int_bonus'],
                    vit_bonus=class_data['vit_bonus'],
                    luk_bonus=class_data['luk_bonus'],
                    stat_growth=class_data['stat_growth']
                )
                created_classes.append(hero_class)
                logger.info(f"Created hero class: {hero_class.name}")
            
            logger.info(f"Successfully initialized {len(created_classes)} hero classes from JSON configuration")
            return created_classes
            
        except Exception as e:
            logger.error(f"Error initializing hero classes: {e}")
            raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_hero_classes())
