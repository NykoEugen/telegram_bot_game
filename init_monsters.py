"""
Initialize monster classes in the database.
"""

import logging
from database import get_db_session, create_monster_class, get_all_monster_classes
from monster_system import MonsterClasses

logger = logging.getLogger(__name__)


async def init_monster_classes():
    """Initialize all monster classes in the database."""
    async for session in get_db_session():
        try:
            # Check if classes already exist
            existing_classes = await get_all_monster_classes(session)
            if existing_classes:
                logger.info(f"Monster classes already exist: {[c.name for c in existing_classes]}")
                return existing_classes
            
            # Create all monster classes
            classes_data = MonsterClasses.get_all_classes()
            created_classes = []
            
            for class_data in classes_data:
                monster_class = await create_monster_class(
                    session=session,
                    name=class_data['name'],
                    description=class_data['description'],
                    monster_type=class_data['monster_type'],
                    difficulty=class_data['difficulty'],
                    base_str=class_data['base_str'],
                    base_agi=class_data['base_agi'],
                    base_int=class_data['base_int'],
                    base_vit=class_data['base_vit'],
                    base_luk=class_data['base_luk'],
                    stat_growth=class_data['stat_growth']
                )
                created_classes.append(monster_class)
                logger.info(f"Created monster class: {monster_class.name}")
            
            logger.info(f"Successfully initialized {len(created_classes)} monster classes")
            return created_classes
            
        except Exception as e:
            logger.error(f"Error initializing monster classes: {e}")
            raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_monster_classes())
