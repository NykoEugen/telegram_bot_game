"""
Quest loader for loading quest data from JSON files.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class QuestLoader:
    """Class for loading quest data from JSON configuration files."""
    
    _quests_data = None
    
    @classmethod
    def _load_quests_data(cls) -> List[Dict[str, Any]]:
        """Load quests data from JSON file."""
        if cls._quests_data is None:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(current_dir, 'data', 'quest_nodes.json')
            
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls._quests_data = data['quests']
            except FileNotFoundError:
                raise FileNotFoundError(f"Quest nodes JSON file not found at {json_file_path}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in quest nodes file: {e}")
        
        return cls._quests_data
    
    @classmethod
    def get_all_quests(cls) -> List[Dict[str, Any]]:
        """Get all quests data from JSON file."""
        return cls._load_quests_data()
    
    @classmethod
    def get_quest_by_id(cls, quest_id: int) -> Optional[Dict[str, Any]]:
        """Get quest data by ID."""
        quests_data = cls._load_quests_data()
        
        for quest_data in quests_data:
            if quest_data['id'] == quest_id:
                return quest_data
        
        return None
    
    @classmethod
    def get_quest_nodes(cls, quest_id: int) -> List[Dict[str, Any]]:
        """Get all nodes for a specific quest."""
        quest_data = cls.get_quest_by_id(quest_id)
        if quest_data:
            return quest_data.get('nodes', [])
        return []
    
    @classmethod
    def get_quest_connections(cls, quest_id: int) -> List[Dict[str, Any]]:
        """Get all connections for a specific quest."""
        quest_data = cls.get_quest_by_id(quest_id)
        if quest_data:
            return quest_data.get('connections', [])
        return []
    
    @classmethod
    def get_node_by_id(cls, quest_id: int, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific node by quest ID and node ID."""
        nodes = cls.get_quest_nodes(quest_id)
        
        for node in nodes:
            if node['id'] == node_id:
                return node
        
        return None
