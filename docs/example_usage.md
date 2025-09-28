# Town System Usage Example

## Getting Started

1. **Start the bot** and use `/start` to register
2. **Enter the town** with `/town` command
3. **Explore** the starting village: Greenbrook Village

## Navigation Flow

### Initial Entry
```
User: /town
Bot: 🏘️ Welcome to Greenbrook Village!
     A peaceful farming village nestled in the valley...
     
     📍 Current Location: Town Center
     The heart of the village. A small fountain sits in...
     
     [🏘️ Explore Town] [🗺️ Town Map] [ℹ️ Town Info]
```

### Exploring the Town
```
User: [🏘️ Explore Town]
Bot: 🔍 Exploring Town Center
     The heart of the village. A small fountain sits in...
     
     Available paths:
     [🚶 Go to Node 2] [🚶 Go to Node 3] [🚶 Go to Node 4] [🚶 Go to Node 5]
     [🔍 Explore Here] [🗺️ Town Map] [🏠 Town Center]
```

### Using the Town Map
```
User: [🗺️ Town Map]
Bot: 🗺️ Town Map - Greenbrook Village
     
     Available locations:
     🏠 Town Center
     🏴‍☠️ The Shadow's Den
     🏰 Guard Barracks
     🏛️ Market Square
     🏨 The Traveler's Rest
     
     [🏠 Town Center] [🏴‍☠️ The Shadow's Den] [🏰 Guard Barracks]
     [🏛️ Market Square] [🏨 The Traveler's Rest]
```

## Location Interactions

### Thieves Guild (The Shadow's Den)
```
User: [🏴‍☠️ The Shadow's Den]
Bot: 🚶 You arrive at The Shadow's Den
     A discreet building with a sign showing a crossed dagger and coin...
     
     [📋 Quest Board] [🗣️ Talk to Adventurers] [⚔️ Guild Services] [🚪 Leave Guild]
```

#### Quest Board
```
User: [📋 Quest Board]
Bot: 📋 Thieves Guild Quest Board
     
     Welcome to the guild, adventurer! Here you can find various quests...
     
     🔍 Available Quests:
     • Dragon's Lair - A fearsome dragon has been terrorizing...
     • Mystery of the Lost Temple - Ancient ruins have been discovered...
     
     [🎯 Dragon's Lair] [🎯 Mystery of the Lost Temple]
     [🔙 Back to Guild] [📋 All Quests]
```

#### Leaving the Guild
```
User: [🚪 Leave Guild]
Bot: 🚪 You leave the building
     
     🏠 Town Center
     
     The heart of the village. A small fountain sits in the middle...
     
     Where would you like to go?
     [🚶 Go to Node 2] [🚶 Go to Node 3] [🚶 Go to Node 4] [🚶 Go to Node 5]
     [🔍 Explore Here] [🗺️ Town Map] [🏠 Town Center]
```

#### Returning from Guild Dialog
```
User: [🔙 Back to Guild] (from quest board dialog)
Bot: 🔙 You return to The Shadow's Den
     
     A discreet building with a sign showing a crossed dagger and coin...
     
     [📋 Quest Board] [🗣️ Talk to Adventurers] [⚔️ Guild Services] [🚪 Leave Guild]
```

### Guard Barracks
```
User: [🏰 Guard Barracks]
Bot: 🚶 You arrive at Guard Barracks
     A sturdy stone building with the village's banner flying above it...
     
     [👹 Monster Hunting] [🚛 Caravan Escort] [🛡️ Guard Duty] [🚪 Leave Barracks]
```

#### Monster Hunting
```
User: [👹 Monster Hunting]
Bot: 👹 Monster Hunting Board
     
     The guard captain points to a board covered with wanted posters...
     
     🔍 Active Bounties:
     • Dragon's Lair - A fearsome dragon has been terrorizing...
     
     [⚔️ Dragon's Lair] [🔙 Back to Barracks] [📋 All Quests]
```

### Market Square
```
User: [🏛️ Market Square]
Bot: 🚶 You arrive at Market Square
     A bustling area where merchants set up their stalls...
     
     [🗣️ Talk to Townspeople] [📢 Check Events] [🏪 Market] [🚪 Leave Square]
```

#### Check Events
```
User: [📢 Check Events]
Bot: 📢 Town Events
     
     You check the town notice board for current events...
     
     🔍 Current Events:
     • Weekly market day tomorrow - extra vendors expected
     • Town meeting this evening to discuss security
     
     📋 Available Quests:
     • Mystery of the Lost Temple - Ancient ruins have been discovered...
     
     [📋 Mystery of the Lost Temple] [🔙 Back to Square] [📋 All Quests]
```

### The Traveler's Rest (Inn)
```
User: [🏨 The Traveler's Rest]
Bot: 🚶 You arrive at The Traveler's Rest
     A cozy inn with warm lighting and the smell of good food...
     
     [😴 Rest] [💾 Save Game] [🗣️ Talk to Innkeeper] [🚪 Leave Inn]
```

#### Rest
```
User: [😴 Rest]
Bot: 😴 Resting at the Inn
     
     You rent a room for the night and get a good night's sleep.
     
     ✨ Benefits:
     • Full health and energy restored
     • All status effects cleared
     • Save point updated
     
     [🔙 Back to Inn]
```

#### Returning from Inn Dialog
```
User: [🔙 Back to Inn] (from rest dialog)
Bot: 🔙 You return to The Traveler's Rest
     
     A cozy inn with warm lighting and the smell of good food...
     
     [😴 Rest] [💾 Save Game] [🗣️ Talk to Innkeeper] [🚪 Leave Inn]
```

## Quest Integration

### Starting a Quest from Guild
```
User: [🎯 Dragon's Lair] (from guild quest board)
Bot: 🎯 Dragon's Lair Quest Started!
     
     A fearsome dragon has been terrorizing the nearby mountains...
     
     [✅ Accept] [❌ Decline] [📋 Menu]
```

### Quest Completion with Rewards Screen
```
User: [✅ Accept] (quest completed)
Bot: 🎉 Quest Completed!
     
     Dragon's Lair
     
     You have successfully defeated the dragon and saved the village!
     
     🏆 Rewards Earned:
     💰 234 Gold
     ⭐ 113 Experience Points
     🐉 Dragon Scale
     ⚔️ Dragon Slayer Badge
     
     🎊 Congratulations on completing this quest!
     
     [🏘️ Return to Town]
```

### Returning to Town from Rewards
```
User: [🏘️ Return to Town]
Bot: 🏘️ Welcome back to Greenbrook Village!
     
     🏠 Town Center
     
     The heart of the village. A small fountain sits in the middle...
     
     Where would you like to go next?
     [🚶 Go to Node 2] [🚶 Go to Node 3] [🚶 Go to Node 4] [🚶 Go to Node 5]
     [🔍 Explore Here] [🗺️ Town Map] [🏠 Town Center]
```

### Starting a Quest from Barracks
```
User: [⚔️ Dragon's Lair] (from barracks monster board)
Bot: 🎯 Dragon's Lair Quest Started!
     
     The guard captain has posted a bounty for the dragon...
     
     [✅ Accept] [❌ Decline] [📋 Menu]
```

## Town Information

### Town Info
```
User: [ℹ️ Town Info]
Bot: ℹ️ Town Information
     
     🏘️ Name: Greenbrook Village
     🏷️ Type: Village
     📝 Description: A peaceful farming village nestled in the valley...
     
     📍 Locations: 5
     ✅ Visited: 3/5
     🕐 Last Visit: 2024-01-15T10:30:00
     
     [🔙 Back to Town]
```

## Advanced Navigation

### Direct Navigation from Map
```
User: [🏨 The Traveler's Rest] (from town map)
Bot: 🚶 You arrive at The Traveler's Rest
     A cozy inn with warm lighting and the smell of good food...
     
     [😴 Rest] [💾 Save Game] [🗣️ Talk to Innkeeper] [🚪 Leave Inn]
```

### Returning to Town Center
```
User: [🏠 Town Center] (from any location)
Bot: 🏠 Town Center
     
     The heart of the village. A small fountain sits in the middle...
     
     Where would you like to go?
     [🚶 Go to Node 2] [🚶 Go to Node 3] [🚶 Go to Node 4] [🚶 Go to Node 5]
     [🔍 Explore Here] [🗺️ Town Map] [🏠 Town Center]
```

## Tips for Players

1. **Explore All Locations**: Each location offers different quests and interactions
2. **Use the Town Map**: Quick navigation between locations
3. **Check Events Regularly**: New quests and events appear on the notice board
4. **Rest at the Inn**: Restore health and save progress
5. **Talk to NPCs**: Get information and rumors about quests
6. **Visit Guild and Barracks**: Different types of quests available
7. **Use Quest Integration**: Start quests directly from appropriate locations
8. **Understand Navigation**: 
   - "Leave" buttons return you to Town Center
   - "Back to" buttons return you to the previous location
   - Quest completion shows rewards screen, then click "Return to Town"

## System Features

- **Persistent Progress**: Your location and visited places are saved
- **Dynamic Quest Integration**: Quests appear in appropriate locations
- **Quest Rewards System**: Shows earned rewards before returning to town
- **Rich Descriptions**: Detailed lore and atmosphere
- **Flexible Navigation**: Multiple ways to move around
- **Expandable**: Easy to add new towns and locations
- **User-Friendly**: Intuitive interface with clear options
