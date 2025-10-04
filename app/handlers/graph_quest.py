"""
Graph Quest handlers for the Telegram bot game.
"""
import logging
import json
from typing import Optional, List, Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic

from app.database import (
    AsyncSessionLocal,
    get_db_session,
    get_user_by_telegram_id,
    get_graph_quest_by_id,
    get_graph_quest_node_by_id,
    get_graph_quest_start_node,
    get_graph_quest_connections,
    get_user_graph_quest_progress,
    create_graph_quest_progress,
    update_graph_quest_progress,
    get_graph_quest_progresses_for_user,
    get_active_quests,
    get_hero_by_user_id,
    get_hero_class_by_id,
    get_hero_for_telegram,
    get_quest_chain_info,
    update_hero_world_flags,
    GraphQuestNode,
    GraphQuestConnection,
    GraphQuestProgress
)
from app.core.hero_system import HeroCalculator
from app.core.encounter_system import EncounterResult, EncounterType, Biome, Difficulty
from app.keyboards import GraphQuestKeyboardBuilder, get_main_menu_keyboard
from app.services.progression import record_progress_messages
from app.core.quest_requirements import check_quest_requirements

logger = logging.getLogger(__name__)

# Create router for graph quest handlers
graph_quest_router = Router()


class GraphQuestManager:
    """Graph quest management class for handling complex quest logic."""

    @staticmethod
    def _load_progress_state(progress: GraphQuestProgress) -> Dict[str, Any]:
        """Return quest state dict with defaults."""
        state: Dict[str, Any] = {}
        if progress.quest_data:
            try:
                state = json.loads(progress.quest_data)
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid quest_data JSON for user %s quest %s. Resetting state.",
                    progress.user_id,
                    progress.quest_id
                )
                state = {}

        if not isinstance(state, dict):
            state = {}

        state.setdefault("completed_encounters", [])
        state.setdefault("active_encounter", None)
        state.setdefault("needs_recovery", False)
        state.setdefault("recovery_node", None)
        state.setdefault("hero_debuff", None)
        state.setdefault("previous_node", None)
        return state

    @staticmethod
    def _serialize_encounter(encounter: EncounterResult) -> Dict[str, Any]:
        """Convert EncounterResult to JSON-friendly dict."""
        return {
            "monster_name": encounter.monster_name,
            "monster_class": encounter.monster_class,
            "encounter_type": encounter.encounter_type.value,
            "biome": encounter.biome.value,
            "difficulty": encounter.difficulty.value,
            "is_ambush": encounter.is_ambush,
            "is_boss": encounter.is_boss,
            "special_modifiers": encounter.special_modifiers or {}
        }

    @staticmethod
    def _deserialize_encounter(data: Optional[Dict[str, Any]]) -> Optional[EncounterResult]:
        """Recreate EncounterResult from stored data."""
        if not data:
            return None

        try:
            return EncounterResult(
                monster_name=data["monster_name"],
                monster_class=data["monster_class"],
                encounter_type=EncounterType(data["encounter_type"]),
                biome=Biome(data["biome"]),
                difficulty=Difficulty(data["difficulty"]),
                is_ambush=data.get("is_ambush", False),
                is_boss=data.get("is_boss", False),
                special_modifiers=data.get("special_modifiers") or {}
            )
        except (KeyError, ValueError):
            logger.warning("Failed to deserialize encounter data: %s", data)
            return None

    @staticmethod
    def _parse_world_flags(hero) -> Dict[str, Any]:
        if not hero or not getattr(hero, 'world_flags', None):
            return {}
        try:
            flags = json.loads(hero.world_flags)
            return flags if isinstance(flags, dict) else {}
        except json.JSONDecodeError:
            logger.warning("Invalid world_flags JSON for hero %s", getattr(hero, 'id', '?'))
            return {}

    @staticmethod
    def _parse_connection_payload(connection: GraphQuestConnection) -> Dict[str, Any]:
        if not connection.condition_data:
            return {}
        try:
            payload = json.loads(connection.condition_data)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            logger.warning(
                "Invalid connection condition JSON for connection %s", connection.id
            )
            return {}

    @staticmethod
    def _connection_allowed(hero_flags: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        conditions = payload.get('conditions') if isinstance(payload, dict) else None
        if not conditions:
            return True

        flag_conditions = conditions.get('world_flags') if isinstance(conditions, dict) else None
        if flag_conditions:
            required = flag_conditions.get('has', {}) if isinstance(flag_conditions, dict) else {}
            if isinstance(required, dict):
                for key, expected in required.items():
                    if hero_flags.get(key) != expected:
                        return False

            missing = flag_conditions.get('missing') if isinstance(flag_conditions, dict) else None
            if missing:
                for key in missing:
                    if key in hero_flags:
                        return False

        return True

    @staticmethod
    def _filter_connections_for_flags(
        hero_flags: Dict[str, Any],
        connections: List[GraphQuestConnection]
    ) -> List[GraphQuestConnection]:
        filtered: List[GraphQuestConnection] = []
        for connection in connections:
            payload = GraphQuestManager._parse_connection_payload(connection)
            if GraphQuestManager._connection_allowed(hero_flags, payload):
                filtered.append(connection)
        return filtered

    @staticmethod
    async def _apply_connection_effects(
        session,
        hero,
        payload: Dict[str, Any]
    ) -> None:
        if not hero or not payload:
            return

        effects = payload.get('effects') if isinstance(payload, dict) else None
        if not effects:
            return

        world_flags = effects.get('world_flags') if isinstance(effects, dict) else None
        if not world_flags:
            return

        set_flags = world_flags.get('set') if isinstance(world_flags, dict) else None
        clear_flags = world_flags.get('clear') if isinstance(world_flags, dict) else None

        updated_flags = await update_hero_world_flags(
            session,
            hero.id,
            set_flags=set_flags if isinstance(set_flags, dict) else None,
            clear_flags=clear_flags if isinstance(clear_flags, (list, tuple, set)) else None
        )
        hero.world_flags = json.dumps(updated_flags, ensure_ascii=False)

    @staticmethod
    def _parse_node_payload(node: GraphQuestNode) -> Dict[str, Any]:
        if not node.node_data:
            return {}
        try:
            payload = json.loads(node.node_data)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            logger.warning("Invalid node payload JSON for node %s", node.id)
            return {}

    @staticmethod
    async def _apply_node_effects(session, hero, node_payload: Dict[str, Any]) -> None:
        if not hero or not node_payload:
            return

        world_flags = node_payload.get('world_flags') if isinstance(node_payload, dict) else None
        if not world_flags:
            return

        set_flags = world_flags.get('set') if isinstance(world_flags, dict) else None
        clear_flags = world_flags.get('clear') if isinstance(world_flags, dict) else None

        updated_flags = await update_hero_world_flags(
            session,
            hero.id,
            set_flags=set_flags if isinstance(set_flags, dict) else None,
            clear_flags=clear_flags if isinstance(clear_flags, (list, tuple, set)) else None
        )
        hero.world_flags = json.dumps(updated_flags, ensure_ascii=False)

    @staticmethod
    async def _apply_chain_step(session, hero, quest_id: int) -> None:
        if not hero:
            return

        chain_info = await get_quest_chain_info(session, quest_id)
        if not chain_info:
            return

        chain_id = chain_info.get('id')
        step = chain_info.get('step')
        if not chain_id or step is None:
            return

        set_flags = {
            f"{chain_id}.step": step,
            f"{chain_id}.completed": True,
        }

        updated_flags = await update_hero_world_flags(
            session,
            hero.id,
            set_flags=set_flags,
        )
        hero.world_flags = json.dumps(updated_flags, ensure_ascii=False)

    @staticmethod
    async def _save_progress_state(
        session,
        progress: GraphQuestProgress,
        state: Dict[str, Any]
    ) -> GraphQuestProgress:
        """Persist quest state JSON."""
        return await update_graph_quest_progress(
            session,
            progress,
            quest_data=json.dumps(state)
        )

    @staticmethod
    def _resolve_previous_node_id(
        progress: GraphQuestProgress,
        node_id: int,
        state: Dict[str, Any]
    ) -> Optional[int]:
        """Determine the most plausible previous node for retreat logic."""
        prev_node_id = state.get('previous_node')
        if isinstance(prev_node_id, int) and prev_node_id != node_id:
            return prev_node_id

        visited_nodes: List[int] = []
        try:
            raw_visited = json.loads(progress.visited_nodes or "[]")
            if isinstance(raw_visited, list):
                visited_nodes = [n for n in raw_visited if isinstance(n, int)]
        except json.JSONDecodeError:
            logger.warning(
                "Invalid visited_nodes JSON for progress %s during flee handling.",
                progress.id
            )

        if visited_nodes:
            for idx in range(len(visited_nodes) - 1, -1, -1):
                if visited_nodes[idx] == node_id:
                    if idx > 0:
                        return visited_nodes[idx - 1]
                    break

            if visited_nodes[-1] != node_id:
                return visited_nodes[-1]

        return None

    @staticmethod
    def _get_encounter_manager():
        """Lazy import EncounterManager to avoid circular imports."""
        from app.handlers.encounter import EncounterManager
        return EncounterManager

    @staticmethod
    async def _get_user_hero(session, telegram_user_id: int):
        """Fetch hero using either internal or telegram user id for compatibility."""
        hero = await get_hero_by_user_id(session, telegram_user_id)
        if hero:
            return hero

        user = await get_user_by_telegram_id(session, telegram_user_id)
        if user:
            hero = await get_hero_by_user_id(session, user.id)
        return hero

    @staticmethod
    async def _is_hero_fully_healed(session, user_id: int) -> bool:
        """Check if hero HP equals max HP."""
        hero = await GraphQuestManager._get_user_hero(session, user_id)
        if not hero:
            return False

        hero_class = await get_hero_class_by_id(session, hero.hero_class_id)
        if not hero_class:
            return False

        stats = HeroCalculator.create_hero_stats(hero, hero_class)
        return hero.current_hp >= stats.hp_max

    @staticmethod
    async def _set_hero_debuff(
        session,
        progress: GraphQuestProgress,
        state: Dict[str, Any],
        debuff: Optional[Dict[str, Any]]
    ) -> GraphQuestProgress:
        """Persist hero debuff info in quest state."""
        state['hero_debuff'] = debuff
        return await GraphQuestManager._save_progress_state(session, progress, state)

    @staticmethod
    async def apply_hero_debuff(
        user_id: int,
        quest_id: int,
        debuff: Optional[Dict[str, Any]]
    ) -> None:
        """Public helper to update hero debuff for a quest."""
        async with AsyncSessionLocal() as session:
            progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if not progress:
                return

            state = GraphQuestManager._load_progress_state(progress)
            await GraphQuestManager._set_hero_debuff(session, progress, state, debuff)

    @staticmethod
    async def clear_recovery_state(
        session,
        user_id: int
    ) -> None:
        """Clear recovery flags and reactivate quests after the hero fully heals."""
        progresses = await get_graph_quest_progresses_for_user(
            session,
            user_id,
            statuses=['active', 'paused']
        )

        for progress in progresses:
            state = GraphQuestManager._load_progress_state(progress)
            changed = False

            if state.get('needs_recovery'):
                state['needs_recovery'] = False
                changed = True

            if state.get('hero_debuff'):
                state['hero_debuff'] = None
                changed = True

            if changed:
                progress = await GraphQuestManager._save_progress_state(session, progress, state)

            if progress.status == 'paused' and not state.get('needs_recovery'):
                await update_graph_quest_progress(session, progress, status='active')

    @staticmethod
    async def start_graph_quest(user_id: int, quest_id: int) -> Optional[dict]:
        """
        Start a graph quest for a user.
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID to start
            
        Returns:
            Dictionary with quest info and start node, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Check if user exists
            user = await get_user_by_telegram_id(session, user_id)
            if not user:
                return None
            
            # Get quest
            quest = await get_graph_quest_by_id(session, quest_id)
            if not quest or not quest.is_active:
                return None

            hero = await get_hero_for_telegram(session, user_id)
            hero_flags = GraphQuestManager._parse_world_flags(hero)
            
            # Check if user already has progress on this quest
            existing_progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if existing_progress:
                state = GraphQuestManager._load_progress_state(existing_progress)

                if state.get('needs_recovery'):
                    hero_fully_healed = await GraphQuestManager._is_hero_fully_healed(session, user.id)
                    if hero_fully_healed:
                        state['needs_recovery'] = False
                        existing_progress = await update_graph_quest_progress(
                            session,
                            existing_progress,
                            status='active'
                        )
                        existing_progress = await GraphQuestManager._save_progress_state(session, existing_progress, state)
                    else:
                        current_node = await get_graph_quest_node_by_id(session, existing_progress.current_node_id)
                        return {
                            'quest': quest,
                            'current_node': current_node,
                            'connections': [],
                            'progress': existing_progress,
                            'recovery_required': True
                        }

                if existing_progress.status == 'active':
                    current_node = await get_graph_quest_node_by_id(session, existing_progress.current_node_id)
                    connections = await get_graph_quest_connections(session, existing_progress.current_node_id)
                    connections = GraphQuestManager._filter_connections_for_flags(hero_flags, connections)
                    return {
                        'quest': quest,
                        'current_node': current_node,
                        'connections': connections,
                        'progress': existing_progress
                    }
            
            requirement_result = await check_quest_requirements(
                session=session,
                quest_id=quest.id,
                user_id=user_id,
                hero_id=hero.id if hero else None,
            )
            if not requirement_result.met:
                return {
                    'quest': quest,
                    'locked_reasons': requirement_result.missing_reasons,
                    'requirements': requirement_result.requirements,
                }

            # Get start node
            start_node = await get_graph_quest_start_node(session, quest_id)
            if not start_node:
                return None
            
            # Get connections from start node
            connections = await get_graph_quest_connections(session, start_node.id)
            connections = GraphQuestManager._filter_connections_for_flags(hero_flags, connections)
            
            # Create new progress with empty encounter state
            initial_state = {
                "completed_encounters": [],
                "active_encounter": None
            }
            progress = await create_graph_quest_progress(
                session,
                user_id,
                quest_id,
                start_node.id,
                json.dumps(initial_state)
            )
            
            return {
                'quest': quest,
                'current_node': start_node,
                'connections': connections,
                'progress': progress
            }
    
    @staticmethod
    async def process_graph_quest_choice(
        user_id: int, 
        quest_id: int, 
        node_id: int, 
        connection_id: int
    ) -> Optional[dict]:
        """
        Process user's quest choice by following a connection.
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID
            node_id: Current node ID
            connection_id: Connection ID to follow
            
        Returns:
            Dictionary with updated quest state, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Get user progress
            progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if not progress or progress.status != 'active':
                return None

            quest_state = GraphQuestManager._load_progress_state(progress)

            hero = await GraphQuestManager._get_user_hero(session, user_id)
            hero_flags = GraphQuestManager._parse_world_flags(hero)

            if quest_state.get('needs_recovery'):
                if await GraphQuestManager._is_hero_fully_healed(session, user_id):
                    quest_state['needs_recovery'] = False
                    quest_state['recovery_node'] = None
                    progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)
                    progress = await update_graph_quest_progress(session, progress, status='active')
                else:
                    return {
                        'quest': await get_graph_quest_by_id(session, quest_id),
                        'current_node': await get_graph_quest_node_by_id(session, progress.current_node_id),
                        'connections': [],
                        'progress': progress,
                        'completed': False,
                        'connection_used': None,
                        'encounter': None,
                        'recovery_required': True
                    }

            # Get current node
            current_node = await get_graph_quest_node_by_id(session, node_id)
            if not current_node:
                return None

            quest_state['previous_node'] = current_node.id
            progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)

            # Get all connections from current node
            all_connections = await get_graph_quest_connections(session, node_id)
            connections = GraphQuestManager._filter_connections_for_flags(hero_flags, all_connections)

            # Find the specific connection
            target_connection = None
            for conn in connections:
                if conn.id == connection_id:
                    target_connection = conn
                    break
            
            if not target_connection:
                return None

            connection_payload = GraphQuestManager._parse_connection_payload(target_connection)
            await GraphQuestManager._apply_connection_effects(session, hero, connection_payload)
            hero_flags = GraphQuestManager._parse_world_flags(hero)

            # Get the target node
            next_node = await get_graph_quest_node_by_id(session, target_connection.to_node_id)
            if not next_node:
                return None

            node_payload = GraphQuestManager._parse_node_payload(next_node)

            # Update progress to next node
            await update_graph_quest_progress(session, progress, current_node_id=next_node.id)

            # Reset recovery flag when moving forward
            quest_state = GraphQuestManager._load_progress_state(progress)
            if quest_state.get('needs_recovery'):
                quest_state['needs_recovery'] = False
                quest_state['recovery_node'] = None
                progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)

            await GraphQuestManager._apply_node_effects(session, hero, node_payload)
            hero_flags = GraphQuestManager._parse_world_flags(hero)

            # Get connections from next node
            next_connections_all = await get_graph_quest_connections(session, next_node.id)
            next_connections = GraphQuestManager._filter_connections_for_flags(hero_flags, next_connections_all)

            # Check if quest is completed
            completed = next_node.is_final

            if completed:
                await update_graph_quest_progress(session, progress, status='completed')
                await GraphQuestManager._apply_chain_step(session, hero, quest_id)

            # Check for encounters in the new node
            encounter = None
            active_encounter = quest_state.get("active_encounter") or {}
            encounter_completed = next_node.id in quest_state.get("completed_encounters", [])

            # Reuse pending encounter if it matches this node
            if active_encounter.get("node_id") == next_node.id:
                encounter = GraphQuestManager._deserialize_encounter(active_encounter.get("encounter"))

            # Generate a new encounter only if node has tags and it wasn't completed
            encounter_tags = (
                node_payload.get('encounter_tags')
                if isinstance(node_payload, dict)
                else None
            )

            if not encounter and not encounter_completed and encounter_tags:
                EncounterManager = GraphQuestManager._get_encounter_manager()
                encounter = await EncounterManager.trigger_encounter(
                    user_id,
                    {
                        'id': next_node.id,
                        'quest_id': quest_id,
                        'encounter_tags': encounter_tags
                    }
                )

                if encounter:
                    quest_state['active_encounter'] = {
                        'quest_id': quest_id,
                        'node_id': next_node.id,
                        'status': 'pending',
                        'encounter': GraphQuestManager._serialize_encounter(encounter)
                    }
                    progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)

            # Clear encounter state if none needed
            if not encounter and active_encounter:
                quest_state['active_encounter'] = None
                progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)

            return {
                'quest': await get_graph_quest_by_id(session, quest_id),
                'current_node': next_node,
                'connections': next_connections,
                'progress': progress,
                'completed': completed,
                'connection_used': target_connection,
                'encounter': encounter
            }

    @staticmethod
    async def resolve_encounter_outcome(
        user_id: int,
        quest_id: int,
        node_id: int,
        outcome: str,
        combat_summary: Optional[str] = None,
        failure_note: Optional[str] = None
    ) -> Optional[dict]:
        """Apply encounter outcome and return next quest message/keyboard."""
        async with AsyncSessionLocal() as session:
            progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if not progress or progress.status != 'active':
                return None

            quest_state = GraphQuestManager._load_progress_state(progress)
            active_encounter = quest_state.get('active_encounter') or {}

            if active_encounter.get('node_id') != node_id:
                return None

            encounter = GraphQuestManager._deserialize_encounter(active_encounter.get('encounter'))
            quest = await get_graph_quest_by_id(session, quest_id)
            node = await get_graph_quest_node_by_id(session, node_id)
            hero = await GraphQuestManager._get_user_hero(session, user_id)
            hero_flags = GraphQuestManager._parse_world_flags(hero)

            connections_all = await get_graph_quest_connections(session, node_id)
            connections = GraphQuestManager._filter_connections_for_flags(hero_flags, connections_all)

            EncounterManager = GraphQuestManager._get_encounter_manager()

            if outcome == 'victory':
                completed = set(quest_state.get('completed_encounters', []))
                completed.add(node_id)
                quest_state['completed_encounters'] = list(completed)
                quest_state['active_encounter'] = None
                quest_state['hero_debuff'] = None
                progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)

                summary_lines = [
                    f"{hbold('⚔️ Бій завершився перемогою!')}",
                    f"{hbold(node.title)}",
                    node.description
                ]
                if combat_summary:
                    summary_lines.append("")
                    summary_lines.append(combat_summary)

                quest_text = "\n".join(summary_lines)
                keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
                    quest_id,
                    node_id,
                    connections
                )

            elif outcome == 'defeat':
                quest_state['needs_recovery'] = True
                quest_state['recovery_node'] = node_id
                quest_state['active_encounter'] = None
                quest_state['hero_debuff'] = None
                quest_state['previous_node'] = None
                progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)
                await update_graph_quest_progress(session, progress, status='paused')

                base_note = failure_note or "💀 Ви були переможені і повернулися до міста." 
                quest_text = (
                    f"{hbold(base_note)}\n\n"
                    f"Відновіть здоров'я у місті, перш ніж продовжити пригоду."
                )
                keyboard = get_main_menu_keyboard()

            elif outcome == 'flee_success':
                prev_node_id = GraphQuestManager._resolve_previous_node_id(
                    progress,
                    node_id,
                    quest_state
                )

                if not prev_node_id:
                    prev_node_id = node_id

                try:
                    visited_nodes = json.loads(progress.visited_nodes or "[]")
                except json.JSONDecodeError:
                    visited_nodes = []

                if (
                    isinstance(visited_nodes, list)
                    and visited_nodes
                    and visited_nodes[-1] == node_id
                ):
                    visited_nodes = visited_nodes[:-1]
                    progress.visited_nodes = json.dumps(visited_nodes)

                quest_state['active_encounter'] = None
                quest_state['recovery_node'] = node_id
                quest_state['previous_node'] = prev_node_id
                progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)
                progress = await update_graph_quest_progress(
                    session,
                    progress,
                    current_node_id=prev_node_id
                )

                prev_node = await get_graph_quest_node_by_id(session, prev_node_id)
                prev_connections_all = await get_graph_quest_connections(session, prev_node_id)
                prev_connections = GraphQuestManager._filter_connections_for_flags(
                    hero_flags,
                    prev_connections_all
                )

                note = failure_note or "🏃 Ви відступили до попередньої точки. На вас накладено дебаф." 
                quest_text = (
                    f"{hbold(note)}\n\n"
                    f"{hbold(prev_node.title)}\n"
                    f"{prev_node.description}\n\n"
                    f"Оберіть нову дію."
                )
                keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
                    quest_id,
                    prev_node_id,
                    prev_connections
                )

            else:  # flee_failure or other retry states
                active_encounter['status'] = 'pending'
                quest_state['active_encounter'] = active_encounter
                progress = await GraphQuestManager._save_progress_state(session, progress, quest_state)

                note = failure_note or "❌ Не вдалося втекти! Бій триває з додатковим штрафом." 
                encounter_message = (
                    f"{hbold(note)}\n\n"
                    f"{EncounterManager.format_encounter_message(encounter) if encounter else ''}"
                )

                quest_text = (
                    f"{encounter_message}\n\n"
                    f"{hbold(node.title)}\n"
                    f"{node.description}\n\n"
                    f"Бій відновлюється негайно."
                )
                keyboard = GraphQuestKeyboardBuilder.encounter_keyboard(
                    quest_id,
                    node_id,
                    encounter
                )

            return {
                'quest': quest,
                'node': node,
                'text': quest_text,
                'keyboard': keyboard,
                'encounter': encounter
            }
    
    @staticmethod
    async def get_quest_map(user_id: int, quest_id: int) -> Optional[dict]:
        """
        Get a visual representation of the quest graph for the user.
        
        Args:
            user_id: Telegram user ID
            quest_id: Quest ID
            
        Returns:
            Dictionary with quest map data, or None if failed
        """
        async with AsyncSessionLocal() as session:
            # Get quest
            quest = await get_graph_quest_by_id(session, quest_id)
            if not quest:
                return None
            
            # Get user progress
            progress = await get_user_graph_quest_progress(session, user_id, quest_id)
            if not progress:
                return None
            
            # Get all nodes for the quest
            from app.database import get_graph_quest_nodes
            nodes = await get_graph_quest_nodes(session, quest_id)
            
            # Get visited nodes
            visited_nodes = json.loads(progress.visited_nodes or "[]")
            
            # Create map data
            map_data = {
                'quest': quest,
                'current_node_id': progress.current_node_id,
                'visited_nodes': visited_nodes,
                'nodes': []
            }
            
            for node in nodes:
                node_info = {
                    'id': node.id,
                    'title': node.title,
                    'type': node.node_type,
                    'is_visited': node.id in visited_nodes,
                    'is_current': node.id == progress.current_node_id,
                    'is_final': node.is_final
                }
                map_data['nodes'].append(node_info)
            
            return map_data


# Graph Quest command handlers (now handled by unified /quest command)


@graph_quest_router.message(Command("quest_map"))
async def cmd_quest_map(message: Message):
    """Show quest map for current active quest."""
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{hbold('Quest Map Command')}\n\n"
            f"Usage: /quest_map <quest_id>\n"
            f"Shows your progress through the quest graph."
        )
        return
    
    try:
        quest_id = int(args[1])
    except ValueError:
        await message.answer("Invalid quest ID. Please provide a number.")
        return
    
    user_id = message.from_user.id
    
    # Check if this is a graph quest (ID >= 1)
    if quest_id >= 1:
        map_data = await GraphQuestManager.get_quest_map(user_id, quest_id)
        
        if not map_data:
            await message.answer("Quest not found or you haven't started this quest.")
            return
        
        quest = map_data['quest']
        current_node_id = map_data['current_node_id']
        visited_nodes = map_data['visited_nodes']
        nodes = map_data['nodes']
        
        # Create map visualization
        map_text = f"{hbold('🗺️ Quest Map')}\n\n"
        map_text += f"{hbold(quest.title)}\n\n"
        
        # Show current location
        current_node = next((n for n in nodes if n['id'] == current_node_id), None)
        if current_node:
            map_text += f"📍 {hbold('Current Location:')} {current_node['title']}\n\n"
        
        # Show visited locations
        visited_count = len(visited_nodes)
        total_nodes = len(nodes)
        map_text += f"📊 Progress: {visited_count}/{total_nodes} locations visited\n\n"
        
        # Show all nodes with status
        map_text += f"{hbold('Locations:')}\n"
        for node in nodes:
            status_icon = "📍" if node['is_current'] else "✅" if node['is_visited'] else "❓"
            type_icon = "🏁" if node['is_final'] else "🚪" if node['type'] == 'start' else "🔍"
            map_text += f"{status_icon} {type_icon} {node['title']}\n"
        
        await message.answer(map_text)
    else:
        await message.answer("Quest map is only available for graph quests (ID >= 1).")


# Graph Quest callback handlers
@graph_quest_router.callback_query(F.data.startswith("graph_quest_start:"))
async def handle_graph_quest_start(callback: CallbackQuery):
    """Handle graph quest start callback."""
    quest_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    quest_data = await GraphQuestManager.start_graph_quest(user_id, quest_id)
    
    if not quest_data:
        await callback.answer("Graph quest not found or cannot be started.", show_alert=True)
        return
    
    quest = quest_data['quest']
    current_node = quest_data['current_node']
    connections = quest_data['connections']

    if quest_data.get('recovery_required'):
        quest_text = (
            f"{hbold('Потрібне відновлення!')}\n\n"
            f"Герой надто виснажений після останньої битви. Відновіть здоров'я у місті, щоб продовжити '{quest.title}'."
        )
        keyboard = GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(
            quest.id,
            current_node.id
        )
    else:
        quest_text = (
            f"{hbold('🎯 Graph Quest Started!')}\n\n"
            f"{hbold(quest.title)}\n\n"
            f"{hbold(current_node.title)}\n"
            f"{current_node.description}\n\n"
            f"What will you do?"
        )

        keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
            quest.id, current_node.id, connections
        )

    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@graph_quest_router.callback_query(F.data.startswith("graph_quest_choice:"))
async def handle_graph_quest_choice(callback: CallbackQuery):
    """Handle graph quest choice callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    connection_id = int(parts[3])
    user_id = callback.from_user.id
    
    result = await GraphQuestManager.process_graph_quest_choice(
        user_id, quest_id, node_id, connection_id
    )
    
    if not result:
        await callback.answer("Invalid quest action.", show_alert=True)
        return

    quest = result['quest']
    current_node = result['current_node']
    connections = result['connections']
    connection_used = result['connection_used']
    encounter = result.get('encounter')
    
    if result.get('recovery_required'):
        await callback.message.edit_text(
            f"{hbold('Потрібне відновлення!')}\n\n"
            f"Герой надто виснажений, щоб продовжити пригоду. Відновіть здоров'я, перш ніж рухатися далі.",
            reply_markup=GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(quest.id, current_node.id)
        )
        await callback.answer("Спершу відновіть здоров'я.", show_alert=True)
        return
    
    if result.get('completed'):
        # Quest completed - show rewards screen
        # Import here to avoid circular imports
        from app.handlers.town import show_quest_rewards
        hero_id = None
        async for session in get_db_session():
            hero = await get_hero_for_telegram(session, user_id)
            if hero:
                hero_id = hero.id
            break

        if hero_id:
            for message_text in await record_progress_messages(hero_id, 'graph_quests_completed', 1):
                await callback.message.answer(message_text)
            for message_text in await record_progress_messages(hero_id, 'quests_completed', 1):
                await callback.message.answer(message_text)
        await show_quest_rewards(callback, quest.title, current_node.description)
        return
    elif encounter:
        # Encounter triggered - show encounter options
        EncounterManager = GraphQuestManager._get_encounter_manager()
        encounter_message = EncounterManager.format_encounter_message(encounter)
        quest_text = (
            f"{hbold('✅ Choice Made!')}\n\n"
            f"{hbold(quest.title)}\n\n"
            f"{hbold(current_node.title)}\n"
            f"{current_node.description}\n\n"
            f"{encounter_message}"
        )
        
        # Create keyboard with encounter options
        keyboard = GraphQuestKeyboardBuilder.encounter_keyboard(
            quest.id, current_node.id, encounter
        )
    else:
        # Continue quest normally
        quest_text = (
            f"{hbold('✅ Choice Made!')}\n\n"
            f"{hbold(quest.title)}\n\n"
            f"{hbold(current_node.title)}\n"
            f"{current_node.description}\n\n"
            f"What will you do next?"
        )
        
        keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
            quest.id, current_node.id, connections
        )
    
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer(f"Chose: {connection_used.choice_text or 'Continue'}")


@graph_quest_router.callback_query(F.data.startswith("graph_quest_map:"))
async def handle_graph_quest_map(callback: CallbackQuery):
    """Handle graph quest map callback."""
    quest_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    map_data = await GraphQuestManager.get_quest_map(user_id, quest_id)
    
    if not map_data:
        await callback.answer("Quest not found or you haven't started this quest.", show_alert=True)
        return
    
    quest = map_data['quest']
    current_node_id = map_data['current_node_id']
    visited_nodes = map_data['visited_nodes']
    nodes = map_data['nodes']
    
    # Create map visualization
    map_text = f"{hbold('🗺️ Quest Map')}\n\n"
    map_text += f"{hbold(quest.title)}\n\n"
    
    # Show current location
    current_node = next((n for n in nodes if n['id'] == current_node_id), None)
    if current_node:
        map_text += f"📍 {hbold('Current Location:')} {current_node['title']}\n\n"
    
    # Show visited locations
    visited_count = len(visited_nodes)
    total_nodes = len(nodes)
    map_text += f"📊 Progress: {visited_count}/{total_nodes} locations visited\n\n"
    
    # Show all nodes with status
    map_text += f"{hbold('Locations:')}\n"
    for node in nodes:
        status_icon = "📍" if node['is_current'] else "✅" if node['is_visited'] else "❓"
        type_icon = "🏁" if node['is_final'] else "🚪" if node['type'] == 'start' else "🔍"
        map_text += f"{status_icon} {type_icon} {node['title']}\n"
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(quest.id, current_node_id)
    await callback.message.edit_text(map_text, reply_markup=keyboard)
    await callback.answer()


@graph_quest_router.callback_query(F.data.startswith("graph_quest_menu:"))
async def handle_graph_quest_menu(callback: CallbackQuery):
    """Handle graph quest menu callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        quest = await get_graph_quest_by_id(session, quest_id)
        current_node = await get_graph_quest_node_by_id(session, node_id)
        
        if not quest or not current_node:
            await callback.answer("Quest not found.", show_alert=True)
            return
    
    quest_text = (
        f"{hbold('📋 Graph Quest Menu')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"Current: {current_node.title}\n\n"
        f"Choose an option:"
    )
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_menu_keyboard(quest.id, node_id)
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


@graph_quest_router.callback_query(F.data.startswith("graph_quest_continue:"))
async def handle_graph_quest_continue(callback: CallbackQuery):
    """Handle graph quest continue callback."""
    parts = callback.data.split(":")
    quest_id = int(parts[1])
    node_id = int(parts[2])
    
    async with AsyncSessionLocal() as session:
        quest = await get_graph_quest_by_id(session, quest_id)
        current_node = await get_graph_quest_node_by_id(session, node_id)
        connections_all = await get_graph_quest_connections(session, node_id)
        hero = await get_hero_for_telegram(session, callback.from_user.id)
        hero_flags = GraphQuestManager._parse_world_flags(hero)
        connections = GraphQuestManager._filter_connections_for_flags(hero_flags, connections_all)

        if not quest or not current_node:
            await callback.answer("Quest not found.", show_alert=True)
            return
    
    quest_text = (
        f"{hbold('▶️ Continue Quest')}\n\n"
        f"{hbold(quest.title)}\n\n"
        f"{hbold(current_node.title)}\n"
        f"{current_node.description}\n\n"
        f"What will you do?"
    )
    
    keyboard = GraphQuestKeyboardBuilder.graph_quest_choice_keyboard(
        quest.id, current_node.id, connections
    )
    await callback.message.edit_text(quest_text, reply_markup=keyboard)
    await callback.answer()


def register_graph_quest_handlers(dp):
    """Register graph quest handlers with the dispatcher."""
    dp.include_router(graph_quest_router)
    logger.info("Graph quest handlers registered successfully")
