"""
Graph Quest initialization script to create sample graph-based quests.
"""
import asyncio
import logging
import json
from app.database import (
    AsyncSessionLocal,
    create_quest,
    create_graph_quest_node,
    create_graph_quest_connection,
    get_quest_by_id
)
from app.core.quest_loader import QuestLoader

logger = logging.getLogger(__name__)


async def create_quest_from_json(quest_id: int):
    """Create a quest from JSON configuration."""
    async with AsyncSessionLocal() as session:
        # Check if quest already exists
        existing_quest = await get_quest_by_id(session, quest_id)
        if existing_quest:
            logger.info(f"Quest {quest_id} already exists, skipping creation.")
            return existing_quest
        
        # Load quest data from JSON
        quest_data = QuestLoader.get_quest_by_id(quest_id)
        if not quest_data:
            raise ValueError(f"Quest with ID {quest_id} not found in JSON configuration")
        
        # Create the main quest
        quest = await create_quest(
            session=session,
            title=quest_data['title'],
            description=quest_data['description']
        )
        
        logger.info(f"Created quest: {quest.title} (ID: {quest.id})")
        
        # Create quest nodes
        nodes_data = quest_data.get('nodes', [])
        node_id_to_db_id = {}  # Map JSON node IDs to database node IDs
        
        for node_data in nodes_data:
            # Prepare node_data JSON with encounter_tags if present
            node_json_data = None
            if 'encounter_tags' in node_data:
                node_json_data = json.dumps({
                    'encounter_tags': node_data['encounter_tags']
                })
            
            node = await create_graph_quest_node(
                session=session,
                quest_id=quest.id,
                node_type=node_data['type'],
                title=node_data['title'],
                description=node_data['description'],
                is_start=node_data.get('is_start', False),
                is_final=node_data.get('is_final', False),
                node_data=node_json_data
            )
            node_id_to_db_id[node_data['id']] = node.id
        
        # Create connections
        connections_data = quest_data.get('connections', [])
        for connection_data in connections_data:
            from_node_id = node_id_to_db_id.get(connection_data['from'])
            to_node_id = node_id_to_db_id.get(connection_data['to'])
            
            if from_node_id and to_node_id:
                await create_graph_quest_connection(
                    session=session,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    connection_type=connection_data['type'],
                    choice_text=connection_data.get('choice_text'),
                    order=connection_data.get('order', 1)
                )
        
        await session.commit()
        
        logger.info(f"Quest '{quest.title}' created successfully with {len(nodes_data)} nodes and {len(connections_data)} connections!")
        return quest


async def create_dragon_quest():
    """Create the dragon quest from JSON configuration."""
    return await create_quest_from_json(2)


async def create_mystery_quest():
    """Create the mystery quest from JSON configuration."""
    return await create_quest_from_json(3)


async def main():
    """Main function to initialize graph quests."""
    try:
        # Load all quests from JSON and create them
        all_quests_data = QuestLoader.get_all_quests()
        created_quests = []
        
        for quest_data in all_quests_data:
            quest = await create_quest_from_json(quest_data['id'])
            created_quests.append(quest)
        
        print(f"✅ Graph Quest system initialized!")
        print(f"📋 Created quests:")
        for quest in created_quests:
            print(f"   🎯 {quest.title} (ID: {quest.id})")
        
        print(f"\n🎮 You can now test the graph quest system with:")
        print(f"   /quests - to see available quests")
        for quest in created_quests:
            print(f"   /quest {quest.id} - to start '{quest.title}'")
        
    except Exception as e:
        logger.error(f"Failed to initialize graph quests: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
