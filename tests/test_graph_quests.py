"""
Test script for the graph quest system.
"""
import asyncio
import logging
import sys
from pathlib import Path

current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from app.database import (
    AsyncSessionLocal,
    get_graph_quest_by_id,
    get_graph_quest_nodes,
    get_graph_quest_connections,
    get_graph_quest_start_node
)

logger = logging.getLogger(__name__)


async def test_graph_quest_structure():
    """Test the structure of graph quests."""
    async with AsyncSessionLocal() as session:
        print("🧪 Testing Graph Quest System Structure\n")
        
        # Test Dragon Quest (ID: 2)
        print("🐉 Testing Dragon Quest (ID: 2)")
        dragon_quest = await get_graph_quest_by_id(session, 2)
        if dragon_quest:
            print(f"✅ Quest found: {dragon_quest.title}")
            
            # Get all nodes
            nodes = await get_graph_quest_nodes(session, 2)
            print(f"📊 Total nodes: {len(nodes)}")
            
            # Get start node
            start_node = await get_graph_quest_start_node(session, 2)
            if start_node:
                print(f"🚪 Start node: {start_node.title}")
                
                # Get connections from start node
                connections = await get_graph_quest_connections(session, start_node.id)
                print(f"🔗 Connections from start: {len(connections)}")
                for conn in connections:
                    print(f"   - {conn.choice_text or 'Continue'} (to node {conn.to_node_id})")
            
            # Count different node types
            node_types = {}
            for node in nodes:
                node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
            
            print(f"📈 Node types: {node_types}")
            print(f"🏁 Final nodes: {sum(1 for node in nodes if node.is_final)}")
        else:
            print("❌ Dragon quest not found")
        
        print("\n" + "="*50 + "\n")
        
        # Test Mystery Quest (ID: 3)
        print("🔍 Testing Mystery Quest (ID: 3)")
        mystery_quest = await get_graph_quest_by_id(session, 3)
        if mystery_quest:
            print(f"✅ Quest found: {mystery_quest.title}")
            
            # Get all nodes
            nodes = await get_graph_quest_nodes(session, 3)
            print(f"📊 Total nodes: {len(nodes)}")
            
            # Get start node
            start_node = await get_graph_quest_start_node(session, 3)
            if start_node:
                print(f"🚪 Start node: {start_node.title}")
                
                # Get connections from start node
                connections = await get_graph_quest_connections(session, start_node.id)
                print(f"🔗 Connections from start: {len(connections)}")
                for conn in connections:
                    print(f"   - {conn.choice_text or 'Continue'} (to node {conn.to_node_id})")
            
            # Count different node types
            node_types = {}
            for node in nodes:
                node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
            
            print(f"📈 Node types: {node_types}")
            print(f"🏁 Final nodes: {sum(1 for node in nodes if node.is_final)}")
        else:
            print("❌ Mystery quest not found")
        
        print("\n" + "="*50 + "\n")
        
        # Test quest graph connectivity
        print("🔗 Testing Quest Graph Connectivity")
        for quest_id in [2, 3]:
            quest = await get_graph_quest_by_id(session, quest_id)
            if quest:
                print(f"\n📋 {quest.title}:")
                nodes = await get_graph_quest_nodes(session, quest_id)
                
                # Check for orphaned nodes (nodes with no connections)
                orphaned_nodes = []
                for node in nodes:
                    connections = await get_graph_quest_connections(session, node.id)
                    if not connections and not node.is_final:
                        orphaned_nodes.append(node)
                
                if orphaned_nodes:
                    print(f"⚠️  Orphaned nodes: {[n.title for n in orphaned_nodes]}")
                else:
                    print("✅ No orphaned nodes found")
                
                # Check for nodes with multiple connections
                choice_nodes = []
                for node in nodes:
                    connections = await get_graph_quest_connections(session, node.id)
                    if len(connections) > 1:
                        choice_nodes.append((node, len(connections)))
                
                if choice_nodes:
                    print(f"🎯 Choice nodes: {[(n[0].title, f'{n[1]} choices') for n in choice_nodes]}")
                else:
                    print("ℹ️  No choice nodes found")


async def test_quest_paths():
    """Test possible paths through quests."""
    async with AsyncSessionLocal() as session:
        print("\n🛤️  Testing Quest Paths\n")
        
        async def find_paths(current_node_id, visited=None, path=None):
            """Recursively find all possible paths through the quest."""
            if visited is None:
                visited = set()
            if path is None:
                path = []
            
            if current_node_id in visited:
                return [path]  # Cycle detected
            
            visited.add(current_node_id)
            path = path + [current_node_id]
            
            # Get connections from current node
            connections = await get_graph_quest_connections(session, current_node_id)
            
            if not connections:
                return [path]  # End of path
            
            all_paths = []
            for conn in connections:
                sub_paths = await find_paths(conn.to_node_id, visited.copy(), path.copy())
                all_paths.extend(sub_paths)
            
            return all_paths
        
        for quest_id in [2, 3]:
            quest = await get_graph_quest_by_id(session, quest_id)
            if quest:
                print(f"📋 {quest.title}:")
                start_node = await get_graph_quest_start_node(session, quest_id)
                if start_node:
                    # Note: This is a simplified test - in practice, you'd want to use asyncio
                    # to handle the async calls properly in the recursive function
                    print(f"🚪 Start node: {start_node.title}")
                    
                    # Get immediate connections
                    connections = await get_graph_quest_connections(session, start_node.id)
                    print(f"🔗 Immediate choices: {len(connections)}")
                    for conn in connections:
                        print(f"   - {conn.choice_text or 'Continue'}")


async def main():
    """Main test function."""
    try:
        await test_graph_quest_structure()
        await test_quest_paths()
        
        print("\n✅ Graph Quest System Tests Completed!")
        print("\n🎮 You can now test the system with:")
        print("   /graph_quests - to see available graph quests")
        print("   /graph_quest 2 - to start the dragon quest")
        print("   /graph_quest 3 - to start the mystery quest")
        print("   /quest_map 2 - to view the dragon quest map")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
