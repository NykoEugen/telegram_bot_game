# Graph Quest System Documentation

## Overview

The Graph Quest System is an advanced quest system that allows for complex, branching storylines with multiple paths, choices, and endings. Unlike the simple linear quest system, graph quests support:

- **Multiple branching paths** from any node
- **Complex choice trees** with different outcomes
- **Conditional connections** based on user actions
- **Quest mapping** to visualize progress
- **Non-linear progression** through story nodes

## Database Models

### GraphQuestNode
Enhanced quest node model for graph-based quests:
- `id`: Primary key
- `quest_id`: Reference to quest
- `node_type`: Type of node ('start', 'choice', 'action', 'end', 'condition')
- `title`: Node title
- `description`: Node description
- `node_data`: JSON data for node-specific information
- `is_final`: Whether this is a final node
- `is_start`: Whether this is the starting node
- `created_at`: Creation timestamp

### GraphQuestConnection
Model for connections between quest nodes:
- `id`: Primary key
- `from_node_id`: Source node ID
- `to_node_id`: Target node ID
- `connection_type`: Type of connection ('choice', 'condition', 'default')
- `choice_text`: Text displayed for choice buttons
- `condition_data`: JSON data for conditional logic
- `order`: Order of choices/connections

### GraphQuestProgress
Enhanced progress tracking for graph quests:
- `id`: Primary key
- `user_id`: Telegram user ID
- `quest_id`: Reference to quest
- `current_node_id`: Current node in quest
- `status`: Progress status ('active', 'completed', 'declined', 'paused')
- `started_at`: When quest was started
- `completed_at`: When quest was completed
- `visited_nodes`: JSON array of visited node IDs
- `quest_data`: JSON data for quest state

## Commands

### Graph Quest Commands
- `/graph_quests` - Show available graph quests
- `/graph_quest <id>` - Start a specific graph quest
- `/quest_map <id>` - Show quest map for current progress

### Regular Quest Commands (Still Available)
- `/quests` - Show all available quests (including graph quests)
- `/quest <id>` - Start any quest (linear or graph)

## Sample Graph Quests

### 1. The Dragon's Lair (Quest ID: 2)
A complex adventure with multiple paths through a dragon's lair:

**Structure:**
- **Start Node**: Cave entrance with 3 path choices
- **Choice Nodes**: Different paths (illuminated tunnel, narrow passage, glowing corridor)
- **Action Nodes**: Specific actions (studying murals, harvesting crystals, taking artifacts)
- **Final Encounter**: Dragon confrontation with 3 possible endings
- **Endings**: Redemption, Battle, or Wise Retreat

**Key Features:**
- 3 initial path choices
- Multiple sub-choices within each path
- All paths converge to final encounter
- 3 different endings based on choices

### 2. The Missing Artifact (Quest ID: 3)
A detective mystery with investigation and deduction:

**Structure:**
- **Start Node**: Museum heist discovery
- **Investigation Nodes**: Crime scene examination, suspect interviews
- **Evidence Analysis**: Fabric, footprint, and symbol analysis
- **Deduction Node**: Making the final accusation
- **Endings**: Correct or incorrect accusation

**Key Features:**
- Investigation-based gameplay
- Evidence gathering mechanics
- Multiple suspect interviews
- Critical thinking required for success

## Keyboard Types

### Graph Quest Choice Keyboard
- Multiple choice buttons (🔹) for each available connection
- Continue button (➡️) for default connections
- Menu button (📋) for additional options

### Graph Quest Menu Keyboard
- ▶️ Continue Quest
- 🗺️ Quest Map
- 📊 Progress
- ℹ️ Quest Info

### Graph Quest List Keyboard
- 🎯 Quest titles (one per quest)
- 🔄 Refresh button

### Graph Quest Completion Keyboard
- 🎯 Other Quests
- 📊 My Stats
- 🗺️ View Quest Map

## Quest Map Feature

The quest map provides a visual representation of:
- **Current Location**: Where the user is now
- **Visited Locations**: All nodes the user has been to
- **Unvisited Locations**: Nodes not yet discovered
- **Progress Tracking**: Percentage of quest completion

Map icons:
- 📍 Current location
- ✅ Visited location
- ❓ Unvisited location
- 🏁 Final/ending node
- 🚪 Start node
- 🔍 Regular node

## Usage Examples

### Starting a Graph Quest
```
User: /graph_quests
Bot: Shows list of available graph quests

User: /graph_quest 2
Bot: Starts "The Dragon's Lair" quest with initial choices
```

### Making Choices
```
Bot: "You stand before a dark cave entrance. Three paths lie before you:"
     [🔹 Take the illuminated tunnel]
     [🔹 Go through the narrow passage]
     [🔹 Enter the glowing corridor]
     [📋 Menu]

User: Clicks "Take the illuminated tunnel"
Bot: Advances to tunnel node with new choices
```

### Viewing Quest Map
```
User: /quest_map 2
Bot: Shows visual map of quest progress with current location and visited nodes
```

## Technical Implementation

### Quest Manager
The `GraphQuestManager` class handles:
- Starting graph quests
- Processing user choices
- Managing quest progress
- Generating quest maps

### Database Functions
New database functions support:
- Creating graph quest nodes and connections
- Tracking user progress through graph structure
- Retrieving quest maps and progress data

### Keyboard Builder
The `GraphQuestKeyboardBuilder` creates:
- Dynamic choice keyboards based on available connections
- Menu keyboards with quest-specific options
- Completion keyboards with appropriate actions

## Extending the System

### Creating New Graph Quests

1. **Design the Quest Structure**:
   - Plan nodes and their connections
   - Define choice points and outcomes
   - Create multiple paths and endings

2. **Create Quest and Nodes**:
   ```python
   quest = await create_quest(session, title, description)
   start_node = await create_graph_quest_node(session, quest.id, "start", ...)
   ```

3. **Create Connections**:
   ```python
   await create_graph_quest_connection(
       session, from_node_id, to_node_id, "choice", choice_text
   )
   ```

4. **Add to Initialization**:
   - Add quest creation to `init_graph_quests.py`
   - Update bot startup to initialize new quests

### Advanced Features

The system supports:
- **Conditional Connections**: Connections that depend on quest state
- **Node Data**: JSON data for complex node behavior
- **Quest State**: Persistent data across quest progression
- **Multiple Endings**: Different outcomes based on choices

## File Structure

- `database.py` - Enhanced with graph quest models and functions
- `init_graph_quests.py` - Graph quest initialization script
- `graph_quest_handlers.py` - Graph quest interaction handlers
- `keyboards.py` - Enhanced with graph quest keyboard builders
- `bot.py` - Updated to register graph quest handlers
- `GRAPH_QUEST_SYSTEM.md` - This documentation

## Migration from Linear Quests

The graph quest system is designed to coexist with the existing linear quest system:
- Linear quests (ID 1) continue to work as before
- Graph quests (ID 2+) use the new system
- Both systems share the same quest listing commands
- Users can play both types of quests

## Best Practices

1. **Quest Design**:
   - Keep choice text concise but descriptive
   - Provide meaningful consequences for choices
   - Ensure all paths lead to satisfying conclusions

2. **Node Organization**:
   - Use clear, descriptive node titles
   - Provide sufficient context in descriptions
   - Group related choices logically

3. **Progress Tracking**:
   - Use visited_nodes to prevent backtracking loops
   - Store important quest state in quest_data
   - Provide clear progress indicators

The graph quest system provides a powerful foundation for creating complex, engaging interactive stories that can adapt to user choices and provide multiple paths to success.
