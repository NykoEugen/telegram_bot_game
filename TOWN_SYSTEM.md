# Town System Documentation

## Overview

The Town System is a comprehensive RPG location management system that allows players to explore towns, interact with different locations, and access quests from various sources. The system is built on a node-based architecture that makes it easy to expand and modify.

## Architecture

### Database Models

#### Town
- `id`: Primary key
- `name`: Town name (e.g., "Greenbrook Village")
- `description`: Detailed description of the town
- `town_type`: Type of settlement (village, city, outpost, etc.)
- `is_active`: Whether the town is currently accessible
- `created_at`: Creation timestamp

#### TownNode
- `id`: Primary key
- `town_id`: Foreign key to Town
- `node_type`: Type of location (guild, barracks, square, inn, etc.)
- `name`: Location name
- `description`: Detailed description of the location
- `node_data`: JSON data for location-specific information
- `is_accessible`: Whether the location is currently accessible
- `required_level`: Minimum level required to access
- `created_at`: Creation timestamp

#### TownConnection
- `id`: Primary key
- `from_node_id`: Source node ID
- `to_node_id`: Destination node ID
- `connection_type`: Type of connection (walk, teleport, secret, etc.)
- `is_bidirectional`: Whether the connection works both ways
- `created_at`: Creation timestamp

#### UserTownProgress
- `id`: Primary key
- `user_id`: Telegram user ID
- `town_id`: Town ID
- `current_node_id`: Current location node ID
- `visited_nodes`: JSON array of visited node IDs
- `town_data`: JSON data for town-specific state
- `first_visited_at`: First visit timestamp
- `last_visited_at`: Last visit timestamp

## Available Locations

### Starting Village: Greenbrook Village

#### 1. Town Center
- **Type**: center
- **Description**: The heart of the village with a fountain and main buildings
- **Connections**: All other locations
- **Features**: Central hub for navigation

#### 2. The Shadow's Den (Thieves Guild)
- **Type**: guild
- **Description**: Discreet building for thieves guild operations
- **Features**:
  - Quest board with available quests
  - Talk to adventurers for information
  - Guild services (equipment, fencing, safe houses)
- **Connections**: Town Center, Barracks (secret passage)

#### 3. Guard Barracks
- **Type**: barracks
- **Description**: Stone building with village banner
- **Features**:
  - Monster hunting board
  - Caravan escort missions
  - Guard duty assignments
- **Connections**: Town Center, Square, Guild (secret)

#### 4. Market Square
- **Type**: square
- **Description**: Bustling trading area with stalls
- **Features**:
  - Talk to townspeople for rumors
  - Check town events and announcements
  - Market (trading system - not yet implemented)
- **Connections**: Town Center, Inn

#### 5. The Traveler's Rest (Inn)
- **Type**: inn
- **Description**: Cozy inn with warm atmosphere
- **Features**:
  - Rest to restore health and energy
  - Save game progress
  - Talk to innkeeper for information
- **Connections**: Town Center, Square

## Commands

### `/town`
Enters the starting village and shows the current location with available actions.

### Navigation
- **Town Map**: Shows all available locations with direct navigation
- **Explore Town**: Shows current location with available paths
- **Town Info**: Displays town information and progress

## Quest Integration

The town system integrates with the existing quest system:

### Guild Quests
- Shows available quests from the database
- Filters quests appropriate for guild activities
- Direct quest start buttons

### Barracks Quests
- Shows combat-related quests (dragons, monsters, beasts)
- Military and guard duty missions
- Caravan escort opportunities

### Square Events
- Shows general/exploration quests
- Town events and announcements
- Community-based activities

## Expansion

### Adding New Towns
1. Create town using `create_town()`
2. Add town nodes using `create_town_node()`
3. Create connections using `create_town_connection()`
4. Update initialization in `init_town.py`

### Adding New Location Types
1. Add new node type to database
2. Create specific keyboard in `TownKeyboardBuilder`
3. Add handler in `town_handlers.py`
4. Update emoji mapping in `town_map_keyboard()`

### Adding New Features
1. Extend `node_data` JSON field for location-specific data
2. Add new callback handlers for interactions
3. Update keyboard builders for new options

## Technical Details

### File Structure
- `database.py`: Database models and functions
- `town_handlers.py`: Message and callback handlers
- `keyboards.py`: Inline keyboard builders
- `init_town.py`: Town initialization scripts
- `test_town.py`: Test scripts

### Key Functions
- `create_town()`: Create new town
- `create_town_node()`: Create new location
- `create_town_connection()`: Connect locations
- `get_user_town_progress()`: Get user's town state
- `update_user_town_progress()`: Update user's location

### Callback Data Format
- `town_explore:{town_id}`: Explore town
- `town_map:{town_id}`: Show town map
- `town_move:{town_id}:{from_node}:{to_node}`: Move between locations
- `town_go_to:{town_id}:{node_id}`: Direct navigation
- `town_leave_building:{town_id}:{node_id}`: Leave building and return to town center
- `town_back_to_location:{town_id}:{node_id}`: Return to previous location (from dialog to building)
- `{location_type}_{action}:{town_id}:{node_id}`: Location-specific actions

## Future Enhancements

1. **Trading System**: Implement market functionality
2. **Character Stats**: Add level requirements and stat checks
3. **Dynamic Events**: Random events and encounters
4. **Multiple Towns**: Expand to multiple settlements
5. **Fast Travel**: Teleportation between towns
6. **Guild Membership**: Join and progress through guilds
7. **Reputation System**: Track standing with different factions
8. **Time System**: Day/night cycle affecting availability
9. **Weather System**: Environmental effects on gameplay
10. **NPC Interactions**: More detailed conversations and relationships

## Testing

Run the test suite:
```bash
python test_town.py
```

This will:
1. Initialize the database
2. Create the starting village
3. Test all town nodes and connections
4. Verify the system is working correctly

## Usage Example

1. User types `/town`
2. Bot shows current location (Town Center)
3. User can explore, view map, or get town info
4. User navigates to different locations
5. User interacts with location-specific features
6. User can start quests from appropriate locations
7. User can leave buildings using "Leave" buttons to return to town center
8. **Quest completion automatically returns user to town center**
9. System tracks user progress and visited locations

## Building Navigation

### Leaving Buildings
- **Leave Guild**: Returns to Town Center
- **Leave Barracks**: Returns to Town Center  
- **Leave Square**: Returns to Town Center
- **Leave Inn**: Returns to Town Center

### Returning from Dialogs
- **Back to Guild**: Returns to Guild (from dialog)
- **Back to Barracks**: Returns to Barracks (from dialog)
- **Back to Square**: Returns to Square (from dialog)
- **Back to Inn**: Returns to Inn (from dialog)

### Navigation Flow
1. Enter building (e.g., Guild)
2. Interact with building features (e.g., Talk to Innkeeper)
3. Use "Back to [Building]" button to return to building
4. Use "Leave [Building]" button to return to Town Center
5. Choose next destination from Town Center

## Quest Integration

### Quest Completion
- **Rewards Screen**: Shows earned rewards (gold, experience, items) after quest completion
- **Interactive Return**: User clicks "Return to Town" button to go back to Town Center
- **Welcome Message**: Shows "Welcome back to Greenbrook Village!" message
- **Progress Tracking**: Quest completion is saved and user location is updated

### Quest Rewards System
- **Base Rewards**: Gold (50-200) and Experience Points (100-500) for all quests
- **Dragon Quests**: Additional Dragon Scale and Dragon Slayer Badge
- **Mystery Quests**: Additional Detective's Badge and Ancient Scroll
- **Thief Quests**: Additional Thief's Blade and Stolen Gem
- **Random Generation**: Rewards are randomly generated for variety

### Quest Flow
1. Start quest from town location (Guild, Barracks, Square)
2. Navigate through quest using quest-specific buttons
3. Complete quest objectives
4. **View rewards screen with earned items and experience**
5. **Click "Return to Town" to go back to Town Center**
6. Continue exploring town or start new quests
