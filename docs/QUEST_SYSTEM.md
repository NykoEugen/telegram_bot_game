# Quest System Documentation

## Overview

The quest system provides an interactive graph-based quest experience with inline keyboard buttons for user choices. Users can accept, decline, or access a menu during quest interactions.

## Features

- **Graph-based Quests**: Quests are structured as nodes with connections
- **Interactive Choices**: Users can accept, decline, or access menu options
- **Progress Tracking**: System tracks user progress through quests
- **Custom Keyboards**: Specialized inline keyboards for quest interactions
- **Multiple Endings**: Quests can have different outcomes based on choices

## Database Models

### Quest
- `id`: Primary key
- `title`: Quest title
- `description`: Quest description
- `is_active`: Whether quest is available
- `created_at`: Creation timestamp

### QuestNode
- `id`: Primary key
- `quest_id`: Reference to quest
- `node_type`: Type of node ('start', 'choice', 'end')
- `title`: Node title
- `description`: Node description
- `next_node_id`: ID of next node (for linear progression)
- `is_final`: Whether this is a final node

### QuestProgress
- `id`: Primary key
- `user_id`: Telegram user ID
- `quest_id`: Reference to quest
- `current_node_id`: Current node in quest
- `status`: Progress status ('active', 'completed', 'declined')
- `started_at`: When quest was started
- `completed_at`: When quest was completed (if applicable)

## Commands

- `/quests` - Show available quests
- `/quest <id>` - Start a specific quest
- `/help` - Show all available commands including quest commands

## Keyboard Types

### Quest Choice Keyboard
- ✅ Accept button
- ❌ Decline button  
- 📋 Menu button

### Quest Menu Keyboard
- ▶️ Continue Quest
- 📊 Progress
- ℹ️ Quest Info
- 🔙 Back to Choice

### Quest List Keyboard
- 🎯 Quest titles (one per quest)
- 🔄 Refresh button

### Quest Completion Keyboard
- 🎯 Other Quests
- 📊 My Stats

## Sample Quest: "The Mysterious Forest"

The system includes a sample quest with the following structure:

1. **Start Node**: "Entering the Forest" - User chooses between dark or light path
2. **Choice Nodes**: 
   - Dark Path: Leads to shadow spirit encounter
   - Light Path: Leads to forest guardian encounter
3. **End Nodes**: Different endings based on choices made

## Usage Example

1. User types `/quests` to see available quests
2. User clicks on a quest or types `/quest 1` to start
3. User sees quest description with Accept/Decline/Menu buttons
4. User makes choices and progresses through the quest
5. Quest completes with appropriate ending

## File Structure

- `database.py` - Database models and functions
- `keyboards.py` - Custom keyboard builder
- `quest_handlers.py` - Quest interaction handlers
- `init_quests.py` - Quest initialization script
- `handlers.py` - Updated with quest commands
- `bot.py` - Updated to initialize quests on startup

## Extending the System

To add new quests:

1. Use the database functions to create quest and nodes
2. Define the quest structure with proper node connections
3. The system will automatically handle user interactions

The quest system is designed to be easily extensible for more complex quest structures and multiple branching paths.
