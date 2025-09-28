import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold, hitalic

from app.database import AsyncSessionLocal, create_user, get_user_by_telegram_id, update_user

logger = logging.getLogger(__name__)

# Create router for handlers
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    user = message.from_user
    
    # Get or create user in database
    async with AsyncSessionLocal() as session:
        db_user = await get_user_by_telegram_id(session, user.id)
        
        if not db_user:
            # Create new user
            db_user = await create_user(
                session=session,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                is_bot=user.is_bot,
                language_code=user.language_code
            )
            logger.info(f"Created new user: {db_user}")
        else:
            # Update existing user info if needed
            if (db_user.username != user.username or 
                db_user.first_name != user.first_name or 
                db_user.last_name != user.last_name):
                
                db_user.username = user.username
                db_user.first_name = user.first_name
                db_user.last_name = user.last_name
                db_user = await update_user(session, db_user)
                logger.info(f"Updated user info: {db_user}")
    
    # Send welcome message
    welcome_text = (
        f"👋 {hbold('Welcome!')}\n\n"
        f"Hello {hitalic(user.first_name or user.username or 'there')}!\n\n"
        f"This is a Telegram bot skeleton with:\n"
        f"• Webhook support\n"
        f"• SQLite database\n"
        f"• Async/await architecture\n"
        f"• User management\n\n"
        f"Use /help to see available commands."
    )
    
    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    logger.info(f"Help command from user {message.from_user.id}")
    help_text = (
        f"{hbold('Available Commands:')}\n\n"
        f"/start - Start the bot and register user\n"
        f"/help - Show this help message\n"
        f"/info - Show user information\n"
        f"/ping - Test bot responsiveness\n"
        f"/time - Show current time\n\n"
        f"{hbold('RPG Commands:')}\n"
        f"/hero - Show hero information or create hero\n"
        f"/create_hero - Create a new hero\n"
        f"/classes - Show available hero classes\n"
        f"/stats - Show hero stats (same as /hero)\n"
        f"/town - Enter the starting village\n"
        f"/quests - Show available quests\n"
        f"/quest &lt;id&gt; - Start a specific quest\n\n"
        f"{hbold('Combat Commands:')}\n"
        f"/fight - Start a fight with a random monster\n"
        f"/combat_status - Check current combat status\n"
        f"/end_combat - Force end current combat"
    )
    
    await message.answer(help_text)


@router.message(Command("info"))
async def cmd_info(message: Message):
    """Handle /info command to show user information."""
    user = message.from_user
    
    async with AsyncSessionLocal() as session:
        db_user = await get_user_by_telegram_id(session, user.id)
        
        if db_user:
            info_text = (
                f"{hbold('User Information:')}\n\n"
                f"🆔 ID: {db_user.user_id}\n"
                f"👤 Username: @{db_user.username or 'Not set'}\n"
                f"📛 First Name: {db_user.first_name or 'Not set'}\n"
                f"📛 Last Name: {db_user.last_name or 'Not set'}\n"
                f"🤖 Is Bot: {'Yes' if db_user.is_bot else 'No'}\n"
                f"🌍 Language: {db_user.language_code or 'Not set'}\n"
                f"📅 Created: {db_user.created_at}"
            )
        else:
            info_text = (
                f"{hbold('User Information:')}\n\n"
                f"You are not registered in the database.\n"
                f"Use /start to register."
            )
    
    await message.answer(info_text)


@router.message(Command("ping"))
async def cmd_ping(message: Message):
    """Handle /ping command to test bot responsiveness."""
    start_time = datetime.now()
    
    pong_text = (
        f"🏓 {hbold('Pong!')}\n\n"
        f"Bot is responsive and working properly.\n"
        f"Response time: {(datetime.now() - start_time).total_seconds() * 1000:.2f}ms"
    )
    
    await message.answer(pong_text)


@router.message(Command("time"))
async def cmd_time(message: Message):
    """Handle /time command to show current time."""
    current_time = datetime.now()
    
    time_text = (
        f"🕐 {hbold('Current Time:')}\n\n"
        f"UTC: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"ISO: {current_time.isoformat()}"
    )
    
    await message.answer(time_text)


@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_messages(message: Message, state: FSMContext):
    """Handle all text messages that don't match any command and user is not in FSM state."""
    # Check if user is in any FSM state
    current_state = await state.get_state()
    logger.info(f"General text handler: user {message.from_user.id}, text: '{message.text}', state: {current_state}")
    
    if current_state is not None:
        # User is in FSM state, let specific handlers deal with it
        logger.info(f"User {message.from_user.id} is in FSM state {current_state}, skipping general handler")
        return
    
    user = message.from_user
    
    response_text = (
        f"👋 Hello {user.first_name or user.username or 'there'}!\n\n"
        f"You said: {hitalic(message.text)}\n\n"
        f"Use /help to see available commands."
    )
    
    await message.answer(response_text)
