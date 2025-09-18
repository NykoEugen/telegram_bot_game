"""
Quest initialization script to create sample quests.
"""
import asyncio
import logging
from database import (
    AsyncSessionLocal,
    create_quest,
    create_quest_node,
    get_quest_by_id
)

logger = logging.getLogger(__name__)


async def create_sample_quest():
    """Create a sample quest with multiple nodes."""
    async with AsyncSessionLocal() as session:
        # Check if quest already exists
        existing_quest = await get_quest_by_id(session, 1)
        if existing_quest:
            logger.info("Sample quest already exists, skipping creation.")
            return existing_quest
        
        # Create the main quest
        quest = await create_quest(
            session=session,
            title="The Mysterious Forest",
            description="A simple adventure through a mysterious forest with choices to make."
        )
        
        logger.info(f"Created quest: {quest.title} (ID: {quest.id})")
        
        # Create quest nodes
        # Start node
        start_node = await create_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="start",
            title="Entering the Forest",
            description="You find yourself at the edge of a dark, mysterious forest. The trees seem to whisper secrets, and you can see two paths ahead. One leads deeper into the shadows, while the other follows a sunlit trail."
        )
        
        # Choice node 1 - Dark path
        dark_path_node = await create_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="The Dark Path",
            description="You choose the dark path. As you walk deeper, you hear strange sounds and see glowing eyes in the shadows. A mysterious figure appears before you, offering a choice."
        )
        
        # Choice node 2 - Light path
        light_path_node = await create_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="The Light Path",
            description="You choose the sunlit path. The forest becomes more welcoming, with birds singing and flowers blooming. You meet a friendly forest guardian who offers you guidance."
        )
        
        # End node 1 - Dark path ending
        dark_ending_node = await create_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Shadow's Gift",
            description="The mysterious figure reveals itself to be a shadow spirit. It offers you a powerful artifact in exchange for your courage. You accept the gift and gain the 'Shadow's Blessing' - the ability to see in darkness and move silently.",
            is_final=True
        )
        
        # End node 2 - Light path ending
        light_ending_node = await create_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Guardian's Blessing",
            description="The forest guardian is pleased with your choice. It grants you the 'Light's Blessing' - enhanced wisdom and the ability to heal minor wounds. You feel a warm energy flowing through you.",
            is_final=True
        )
        
        # End node 3 - Decline ending
        decline_ending_node = await create_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="A Wise Retreat",
            description="You decide that the forest is too dangerous and choose to return home. While you didn't gain any special powers, you made a safe choice and learned that sometimes wisdom lies in knowing when to walk away.",
            is_final=True
        )
        
        # Update start node to point to both choice nodes
        start_node.next_node_id = dark_path_node.id
        await session.commit()
        
        # Update choice nodes to point to their respective endings
        dark_path_node.next_node_id = dark_ending_node.id
        light_path_node.next_node_id = light_ending_node.id
        
        # For simplicity, we'll make both paths lead to the same decline option
        # In a more complex system, you'd have separate decline paths
        
        await session.commit()
        
        logger.info("Sample quest created successfully with all nodes!")
        return quest


async def main():
    """Main function to initialize quests."""
    try:
        quest = await create_sample_quest()
        print(f"✅ Quest system initialized!")
        print(f"📋 Created quest: {quest.title}")
        print(f"🆔 Quest ID: {quest.id}")
        print(f"📝 Description: {quest.description}")
        print(f"\n🎮 You can now test the quest system with:")
        print(f"   /quests - to see available quests")
        print(f"   /quest 1 - to start the sample quest")
        
    except Exception as e:
        logger.error(f"Failed to initialize quests: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
