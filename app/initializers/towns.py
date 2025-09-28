"""
Initialize the starting village with all its nodes and connections.
"""
import logging
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def create_starting_village():
    """Create the starting village with all its nodes and connections."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if village already exists
            from app.database import get_town_by_id
            existing_town = await get_town_by_id(session, 1)
            if existing_town:
                logger.info("Starting village already exists, skipping creation")
                return existing_town
            
            # Create the starting village
            from app.database import create_town
            village = await create_town(
                session=session,
                name="Greenbrook Village",
                description="A peaceful farming village nestled in the valley. The perfect place for a young adventurer to begin their journey.",
                town_type="village"
            )
            logger.info(f"Created village: {village.name}")
            
            # Create town nodes
            from app.database import create_town_node
            
            # 1. Town Center (starting location)
            center = await create_town_node(
                session=session,
                town_id=village.id,
                node_type="center",
                name="Town Center",
                description="The heart of the village. A small fountain sits in the middle of the cobblestone square, surrounded by the main buildings. This is where most villagers gather for important announcements.",
                required_level=1
            )
            logger.info(f"Created town center: {center.name}")
            
            # 2. Thieves Guild
            guild = await create_town_node(
                session=session,
                town_id=village.id,
                node_type="guild",
                name="The Shadow's Den",
                description="A discreet building with a sign showing a crossed dagger and coin. This is where the local thieves guild operates. Adventurers can find quests, information, and questionable services here.",
                required_level=1
            )
            logger.info(f"Created guild: {guild.name}")
            
            # 3. Guard Barracks
            barracks = await create_town_node(
                session=session,
                town_id=village.id,
                node_type="barracks",
                name="Guard Barracks",
                description="A sturdy stone building with the village's banner flying above it. The local guards train here and post bounties for dangerous creatures and criminals. A good place to find honest work.",
                required_level=1
            )
            logger.info(f"Created barracks: {barracks.name}")
            
            # 4. Town Square
            square = await create_town_node(
                session=session,
                town_id=village.id,
                node_type="square",
                name="Market Square",
                description="A bustling area where merchants set up their stalls and villagers gather to trade goods and gossip. The notice board here often contains important announcements and local news.",
                required_level=1
            )
            logger.info(f"Created square: {square.name}")
            
            # 5. Inn
            inn = await create_town_node(
                session=session,
                town_id=village.id,
                node_type="inn",
                name="The Traveler's Rest",
                description="A cozy inn with warm lighting and the smell of good food. The innkeeper is friendly and always has stories to tell. This is the perfect place to rest, save your progress, and recover from adventures.",
                required_level=1
            )
            logger.info(f"Created inn: {inn.name}")
            
            # Create connections between nodes
            from app.database import create_town_connection
            
            # All nodes connect to the town center
            await create_town_connection(session, center.id, guild.id, "walk")
            await create_town_connection(session, center.id, barracks.id, "walk")
            await create_town_connection(session, center.id, square.id, "walk")
            await create_town_connection(session, center.id, inn.id, "walk")
            
            # Guild connects to barracks (secret passage)
            await create_town_connection(session, guild.id, barracks.id, "secret", False)
            
            # Square connects to inn (they're close together)
            await create_town_connection(session, square.id, inn.id, "walk")
            
            # Barracks connects to square (patrol route)
            await create_town_connection(session, barracks.id, square.id, "walk")
            
            logger.info("Created all town connections")
            
            return village
            
        except Exception as e:
            logger.error(f"Failed to create starting village: {e}")
            raise


async def create_additional_towns():
    """Create additional towns for future expansion."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if additional towns already exist
            from app.database import get_town_by_id
            existing_town = await get_town_by_id(session, 2)
            if existing_town:
                logger.info("Additional towns already exist, skipping creation")
                return
            
            # Create a larger city
            from app.database import create_town
            city = await create_town(
                session=session,
                name="Riverside City",
                description="A bustling trade city built along the great river. Much larger and more dangerous than the peaceful village, but also offering greater opportunities for wealth and adventure.",
                town_type="city"
            )
            logger.info(f"Created city: {city.name}")
            
            # Create city nodes (more complex than village)
            from app.database import create_town_node
            
            # City center
            city_center = await create_town_node(
                session=session,
                town_id=city.id,
                node_type="center",
                name="Grand Plaza",
                description="The magnificent central plaza of Riverside City, surrounded by grand buildings and bustling with merchants, nobles, and adventurers from all over the realm.",
                required_level=5
            )
            
            # City guild (more advanced)
            city_guild = await create_town_node(
                session=session,
                town_id=city.id,
                node_type="guild",
                name="The Golden Hand",
                description="The most prestigious thieves guild in the region. Only the most skilled and trusted members are allowed access to their exclusive contracts and services.",
                required_level=10
            )
            
            # City barracks (military)
            city_barracks = await create_town_node(
                session=session,
                town_id=city.id,
                node_type="barracks",
                name="Royal Guard Headquarters",
                description="The headquarters of the city's elite guard force. Only the most dangerous and high-paying missions are posted here.",
                required_level=8
            )
            
            # City market (larger)
            city_market = await create_town_node(
                session=session,
                town_id=city.id,
                node_type="square",
                name="Grand Bazaar",
                description="A massive marketplace where exotic goods from distant lands are traded. The perfect place to find rare items and hear news from across the realm.",
                required_level=3
            )
            
            # City inn (luxury)
            city_inn = await create_town_node(
                session=session,
                town_id=city.id,
                node_type="inn",
                name="The Golden Dragon Inn",
                description="The most luxurious inn in the city, frequented by nobles and wealthy merchants. The finest food, drink, and accommodations money can buy.",
                required_level=5
            )
            
            # Create city connections
            from app.database import create_town_connection
            
            # All nodes connect to city center
            await create_town_connection(session, city_center.id, city_guild.id, "walk")
            await create_town_connection(session, city_center.id, city_barracks.id, "walk")
            await create_town_connection(session, city_center.id, city_market.id, "walk")
            await create_town_connection(session, city_center.id, city_inn.id, "walk")
            
            # Additional connections
            await create_town_connection(session, city_market.id, city_inn.id, "walk")
            await create_town_connection(session, city_barracks.id, city_market.id, "walk")
            
            logger.info("Created additional towns")
            
        except Exception as e:
            logger.error(f"Failed to create additional towns: {e}")
            raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_starting_village())
