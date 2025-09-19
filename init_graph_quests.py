"""
Graph Quest initialization script to create sample graph-based quests.
"""
import asyncio
import logging
import json
from database import (
    AsyncSessionLocal,
    create_quest,
    create_graph_quest_node,
    create_graph_quest_connection,
    get_quest_by_id
)

logger = logging.getLogger(__name__)


async def create_dragon_quest():
    """Create a complex graph-based dragon quest with multiple paths and choices."""
    async with AsyncSessionLocal() as session:
        # Check if quest already exists
        existing_quest = await get_quest_by_id(session, 2)
        if existing_quest:
            logger.info("Dragon quest already exists, skipping creation.")
            return existing_quest
        
        # Create the main quest
        quest = await create_quest(
            session=session,
            title="The Dragon's Lair",
            description="A complex adventure with multiple paths, choices, and endings. Navigate through the dragon's lair and make crucial decisions that will determine your fate."
        )
        
        logger.info(f"Created quest: {quest.title} (ID: {quest.id})")
        
        # Create quest nodes
        # Start node
        start_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="start",
            title="The Cave Entrance",
            description="You stand before a dark cave entrance. Ancient runes are carved into the stone, and you can hear distant sounds echoing from within. Three paths lie before you: a well-lit tunnel to the left, a narrow passage straight ahead, and a mysterious glowing corridor to the right.",
            is_start=True
        )
        
        # Choice nodes - Left path
        left_tunnel_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="The Illuminated Tunnel",
            description="You enter the well-lit tunnel. The walls are covered in glowing crystals that provide a warm, magical light. You can see ancient murals depicting dragons and heroes. A fork in the path appears ahead."
        )
        
        # Choice nodes - Center path
        center_passage_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="The Narrow Passage",
            description="You squeeze through the narrow passage. The air is thick with dust and the sound of your footsteps echoes ominously. You find a hidden chamber with three mysterious artifacts: a glowing sword, a ancient tome, and a crystal orb."
        )
        
        # Choice nodes - Right path
        right_corridor_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="The Glowing Corridor",
            description="You step into the glowing corridor. The walls pulse with magical energy, and you feel a strange power coursing through your body. You discover a magical portal that seems to lead deeper into the lair."
        )
        
        # Action nodes - Left path branches
        mural_study_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Studying the Murals",
            description="You carefully study the ancient murals. They tell the story of a great dragon who was once a guardian of the realm, but was corrupted by dark magic. The murals reveal a secret: the dragon can be saved, not destroyed."
        )
        
        crystal_harvest_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Harvesting Crystals",
            description="You carefully extract some of the glowing crystals. They pulse with magical energy and seem to respond to your touch. You feel stronger and more attuned to magic."
        )
        
        # Action nodes - Center path branches
        sword_take_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Taking the Sword",
            description="You grasp the glowing sword. It hums with power and seems to recognize you as worthy. The blade glows brighter, and you feel a connection to ancient warriors who once wielded it."
        )
        
        tome_read_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Reading the Tome",
            description="You open the ancient tome. The pages are written in an old language, but somehow you can understand it. It contains spells and knowledge about dragons, including a ritual to purify corrupted dragons."
        )
        
        orb_touch_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Touching the Orb",
            description="You reach out and touch the crystal orb. Visions flood your mind: you see the dragon's past, its corruption, and a way to save it. The orb grants you the ability to see the truth behind illusions."
        )
        
        # Action nodes - Right path branches
        portal_enter_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Entering the Portal",
            description="You step through the magical portal. You find yourself in a vast chamber filled with floating islands and streams of pure magic. A voice echoes through the chamber, offering you a choice."
        )
        
        magic_absorb_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Absorbing Magic",
            description="You allow the magical energy to flow through you. Your body glows with power, and you feel connected to the very essence of magic itself. You gain the ability to cast powerful spells."
        )
        
        # Final encounter nodes
        dragon_encounter_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="The Dragon's Chamber",
            description="You finally reach the dragon's chamber. A massive, corrupted dragon lies before you, its eyes glowing with dark magic. You can see the pain and suffering in its gaze. How will you approach this final confrontation?"
        )
        
        # Ending nodes
        redemption_ending_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Dragon's Redemption",
            description="Using the knowledge and artifacts you've gathered, you perform the purification ritual. The dragon's corruption fades away, revealing a noble, ancient guardian. The dragon thanks you and grants you the title of 'Dragon Friend' and the power to call upon dragons for aid.",
            is_final=True
        )
        
        battle_ending_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Epic Battle",
            description="You engage in an epic battle with the dragon. Using your weapons and magic, you manage to defeat the corrupted beast. As it falls, the corruption fades, and you realize the dragon was once good. You gain the title of 'Dragon Slayer' and the dragon's hoard.",
            is_final=True
        )
        
        escape_ending_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Wise Retreat",
            description="You realize that the dragon is too powerful and choose to retreat. As you leave, you hear the dragon's voice thanking you for not causing further harm. You gain wisdom and the knowledge that sometimes the bravest choice is to walk away.",
            is_final=True
        )
        
        # Create connections
        # From start node to three main paths
        await create_graph_quest_connection(
            session=session,
            from_node_id=start_node.id,
            to_node_id=left_tunnel_node.id,
            connection_type="choice",
            choice_text="Take the illuminated tunnel",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=start_node.id,
            to_node_id=center_passage_node.id,
            connection_type="choice",
            choice_text="Go through the narrow passage",
            order=2
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=start_node.id,
            to_node_id=right_corridor_node.id,
            connection_type="choice",
            choice_text="Enter the glowing corridor",
            order=3
        )
        
        # Left path connections
        await create_graph_quest_connection(
            session=session,
            from_node_id=left_tunnel_node.id,
            to_node_id=mural_study_node.id,
            connection_type="choice",
            choice_text="Study the murals",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=left_tunnel_node.id,
            to_node_id=crystal_harvest_node.id,
            connection_type="choice",
            choice_text="Harvest the crystals",
            order=2
        )
        
        # Center path connections
        await create_graph_quest_connection(
            session=session,
            from_node_id=center_passage_node.id,
            to_node_id=sword_take_node.id,
            connection_type="choice",
            choice_text="Take the glowing sword",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=center_passage_node.id,
            to_node_id=tome_read_node.id,
            connection_type="choice",
            choice_text="Read the ancient tome",
            order=2
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=center_passage_node.id,
            to_node_id=orb_touch_node.id,
            connection_type="choice",
            choice_text="Touch the crystal orb",
            order=3
        )
        
        # Right path connections
        await create_graph_quest_connection(
            session=session,
            from_node_id=right_corridor_node.id,
            to_node_id=portal_enter_node.id,
            connection_type="choice",
            choice_text="Enter the portal",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=right_corridor_node.id,
            to_node_id=magic_absorb_node.id,
            connection_type="choice",
            choice_text="Absorb the magical energy",
            order=2
        )
        
        # All paths lead to dragon encounter
        await create_graph_quest_connection(
            session=session,
            from_node_id=mural_study_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=crystal_harvest_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=sword_take_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=tome_read_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=orb_touch_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=portal_enter_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=magic_absorb_node.id,
            to_node_id=dragon_encounter_node.id,
            connection_type="default",
            order=1
        )
        
        # Dragon encounter to endings
        await create_graph_quest_connection(
            session=session,
            from_node_id=dragon_encounter_node.id,
            to_node_id=redemption_ending_node.id,
            connection_type="choice",
            choice_text="Try to save the dragon",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=dragon_encounter_node.id,
            to_node_id=battle_ending_node.id,
            connection_type="choice",
            choice_text="Fight the dragon",
            order=2
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=dragon_encounter_node.id,
            to_node_id=escape_ending_node.id,
            connection_type="choice",
            choice_text="Retreat from the chamber",
            order=3
        )
        
        await session.commit()
        
        logger.info("Dragon quest created successfully with all nodes and connections!")
        return quest


async def create_mystery_quest():
    """Create a mystery quest with investigation and deduction elements."""
    async with AsyncSessionLocal() as session:
        # Check if quest already exists
        existing_quest = await get_quest_by_id(session, 3)
        if existing_quest:
            logger.info("Mystery quest already exists, skipping creation.")
            return existing_quest
        
        # Create the mystery quest
        quest = await create_quest(
            session=session,
            title="The Missing Artifact",
            description="A detective story where you must investigate a theft, gather clues, and solve the mystery through careful deduction and choice-making."
        )
        
        logger.info(f"Created quest: {quest.title} (ID: {quest.id})")
        
        # Create quest nodes
        # Start node
        start_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="start",
            title="The Museum Heist",
            description="You arrive at the Grand Museum to find chaos. The legendary 'Crystal of Eternity' has been stolen! The curator is frantic, guards are searching everywhere, and three suspects have been detained. You must investigate and find the real culprit.",
            is_start=True
        )
        
        # Investigation nodes
        examine_crime_scene_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Examining the Crime Scene",
            description="You carefully examine the crime scene. The display case is shattered, but there are no signs of forced entry. You notice three important clues: a piece of fabric caught on the broken glass, a muddy footprint, and a strange symbol drawn in chalk on the floor."
        )
        
        interview_suspects_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="Interviewing Suspects",
            description="You have three suspects to interview: Lady Victoria (a wealthy collector), Professor Blackwood (a museum researcher), and Marcus the Janitor. Each has a different story and alibi. Who do you want to question first?"
        )
        
        # Suspect interview nodes
        interview_victoria_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Interviewing Lady Victoria",
            description="Lady Victoria claims she was at a charity gala all evening. She seems nervous and keeps checking her expensive watch. She mentions that she 'knows the value of such artifacts' and that 'security here is laughable.' You notice she's wearing a dress that matches the fabric found at the scene."
        )
        
        interview_blackwood_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Interviewing Professor Blackwood",
            description="Professor Blackwood is calm and methodical. He explains that he was in his office all night, working on research. He shows you his notes and seems genuinely concerned about the theft. However, you notice the chalk symbol on the floor matches symbols in his research papers."
        )
        
        interview_marcus_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Interviewing Marcus the Janitor",
            description="Marcus is clearly frightened and claims he was cleaning the basement all night. He has an alibi from the night guard, but you notice his work boots have mud on them that matches the footprint at the scene. He seems to know more than he's saying."
        )
        
        # Evidence analysis nodes
        analyze_evidence_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="Analyzing Evidence",
            description="You've gathered several pieces of evidence. Now you need to analyze them carefully. Which piece of evidence do you want to examine more closely?"
        )
        
        fabric_analysis_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Analyzing the Fabric",
            description="The fabric is expensive silk, matching Lady Victoria's dress. However, upon closer inspection, you realize it's been torn recently and has traces of a chemical used in display case cleaning. This suggests the thief was familiar with the museum's security procedures."
        )
        
        footprint_analysis_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Analyzing the Footprint",
            description="The muddy footprint is from a work boot, size 10. It matches Marcus's boots exactly. The mud contains traces of a rare mineral found only in the museum's basement storage area. This suggests the thief had access to restricted areas."
        )
        
        symbol_analysis_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="action",
            title="Analyzing the Symbol",
            description="The chalk symbol is an ancient rune meaning 'hidden knowledge.' It's drawn in a style that matches Professor Blackwood's research notes. However, the chalk used is a special type that only museum staff have access to."
        )
        
        # Deduction nodes
        make_accusation_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="choice",
            title="Making Your Accusation",
            description="Based on your investigation, you believe you know who the real culprit is. The evidence points to one person, but you need to be certain. Who do you accuse?"
        )
        
        # Ending nodes
        correct_accusation_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Truth Revealed",
            description="You've correctly identified the thief! Professor Blackwood confesses that he stole the crystal to prevent it from falling into the wrong hands. He reveals that Lady Victoria was planning to sell it to a criminal organization. You've solved the case and prevented a greater crime.",
            is_final=True
        )
        
        wrong_accusation_node = await create_graph_quest_node(
            session=session,
            quest_id=quest.id,
            node_type="end",
            title="The Wrong Conclusion",
            description="Your accusation was incorrect. The real thief escapes, and the crystal is lost forever. You learn that sometimes the most obvious suspect isn't the guilty party, and that thorough investigation is crucial in solving mysteries.",
            is_final=True
        )
        
        # Create connections
        # From start to investigation options
        await create_graph_quest_connection(
            session=session,
            from_node_id=start_node.id,
            to_node_id=examine_crime_scene_node.id,
            connection_type="choice",
            choice_text="Examine the crime scene",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=start_node.id,
            to_node_id=interview_suspects_node.id,
            connection_type="choice",
            choice_text="Interview the suspects",
            order=2
        )
        
        # From crime scene to suspects
        await create_graph_quest_connection(
            session=session,
            from_node_id=examine_crime_scene_node.id,
            to_node_id=interview_suspects_node.id,
            connection_type="default",
            order=1
        )
        
        # Suspect interview connections
        await create_graph_quest_connection(
            session=session,
            from_node_id=interview_suspects_node.id,
            to_node_id=interview_victoria_node.id,
            connection_type="choice",
            choice_text="Interview Lady Victoria",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=interview_suspects_node.id,
            to_node_id=interview_blackwood_node.id,
            connection_type="choice",
            choice_text="Interview Professor Blackwood",
            order=2
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=interview_suspects_node.id,
            to_node_id=interview_marcus_node.id,
            connection_type="choice",
            choice_text="Interview Marcus the Janitor",
            order=3
        )
        
        # From interviews to evidence analysis
        await create_graph_quest_connection(
            session=session,
            from_node_id=interview_victoria_node.id,
            to_node_id=analyze_evidence_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=interview_blackwood_node.id,
            to_node_id=analyze_evidence_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=interview_marcus_node.id,
            to_node_id=analyze_evidence_node.id,
            connection_type="default",
            order=1
        )
        
        # Evidence analysis connections
        await create_graph_quest_connection(
            session=session,
            from_node_id=analyze_evidence_node.id,
            to_node_id=fabric_analysis_node.id,
            connection_type="choice",
            choice_text="Analyze the fabric",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=analyze_evidence_node.id,
            to_node_id=footprint_analysis_node.id,
            connection_type="choice",
            choice_text="Analyze the footprint",
            order=2
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=analyze_evidence_node.id,
            to_node_id=symbol_analysis_node.id,
            connection_type="choice",
            choice_text="Analyze the symbol",
            order=3
        )
        
        # From evidence analysis to accusation
        await create_graph_quest_connection(
            session=session,
            from_node_id=fabric_analysis_node.id,
            to_node_id=make_accusation_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=footprint_analysis_node.id,
            to_node_id=make_accusation_node.id,
            connection_type="default",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=symbol_analysis_node.id,
            to_node_id=make_accusation_node.id,
            connection_type="default",
            order=1
        )
        
        # Accusation to endings
        await create_graph_quest_connection(
            session=session,
            from_node_id=make_accusation_node.id,
            to_node_id=correct_accusation_node.id,
            connection_type="choice",
            choice_text="Accuse Professor Blackwood",
            order=1
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=make_accusation_node.id,
            to_node_id=wrong_accusation_node.id,
            connection_type="choice",
            choice_text="Accuse Lady Victoria",
            order=2
        )
        
        await create_graph_quest_connection(
            session=session,
            from_node_id=make_accusation_node.id,
            to_node_id=wrong_accusation_node.id,
            connection_type="choice",
            choice_text="Accuse Marcus the Janitor",
            order=3
        )
        
        await session.commit()
        
        logger.info("Mystery quest created successfully with all nodes and connections!")
        return quest


async def main():
    """Main function to initialize graph quests."""
    try:
        dragon_quest = await create_dragon_quest()
        mystery_quest = await create_mystery_quest()
        
        print(f"✅ Graph Quest system initialized!")
        print(f"📋 Created quests:")
        print(f"   🐉 {dragon_quest.title} (ID: {dragon_quest.id})")
        print(f"   🔍 {mystery_quest.title} (ID: {mystery_quest.id})")
        print(f"\n🎮 You can now test the graph quest system with:")
        print(f"   /quests - to see available quests")
        print(f"   /quest 2 - to start the dragon quest")
        print(f"   /quest 3 - to start the mystery quest")
        
    except Exception as e:
        logger.error(f"Failed to initialize graph quests: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
