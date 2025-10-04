import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .cache import close_redis
from .config import Config
from .database import init_db
from .handlers import register_handlers
from .middleware import register_middleware
from .initializers import (
    create_sample_quest,
    create_dragon_quest,
    create_mystery_quest,
    create_starting_village,
    create_additional_towns,
    init_hero_classes,
    init_monster_classes,
    init_items,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(app: web.Application):
    """Application startup handler."""
    await init_db()
    logger.info("Database initialized")
    
    # Initialize sample quests
    try:
        await create_sample_quest()
        logger.info("Sample quests initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize sample quests: {e}")

    # Initialize graph quests
    try:
        await create_dragon_quest()
        await create_mystery_quest()
        logger.info("Graph quests initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize graph quests: {e}")

    # Initialize towns
    try:
        await create_starting_village()
        await create_additional_towns()
        logger.info("Towns initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize towns: {e}")

    # Initialize hero classes
    try:
        await init_hero_classes()
        logger.info("Hero classes initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize hero classes: {e}")

    # Initialize monster classes
    try:
        await init_monster_classes()
        logger.info("Monster classes initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize monster classes: {e}")

    # Initialize item definitions
    try:
        await init_items()
        logger.info("Items initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize items: {e}")


async def on_shutdown(app: web.Application):
    """Application shutdown handler."""
    logger.info("Application shutdown")
    await close_redis()


async def create_app() -> web.Application:
    """Create and configure aiohttp application."""
    Config.validate()

    # Initialize bot and dispatcher
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Register middleware and handlers
    register_middleware(dp)
    register_handlers(dp)
    
    # Create aiohttp application
    app = web.Application()
    app["bot"] = bot
    app["dispatcher"] = dp
    
    # Add startup and shutdown handlers
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Setup webhook handler
    webhook_path = f"/webhook/{Config.BOT_TOKEN}"
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=Config.WEBHOOK_SECRET
    )
    webhook_handler.register(app, path=webhook_path)
    
    # Setup application
    setup_application(app, dp, bot=bot)
    
    return app


async def main():
    """Main function to run the bot."""
    try:
        # Create application
        app = await create_app()
        
        # Run webhook server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner,
            host=Config.WEBHOOK_HOST,
            port=Config.WEBHOOK_PORT
        )
        
        await site.start()
        
        # Set webhook
        webhook_url = f"https://{Config.WEBHOOK_DOMAIN}/webhook/{Config.BOT_TOKEN}"
        await app["bot"].set_webhook(
            url=webhook_url,
            secret_token=Config.WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        
        logger.info(f"Bot started on {Config.WEBHOOK_HOST}:{Config.WEBHOOK_PORT}")
        logger.info(f"Webhook URL: {webhook_url}")
        
        # Keep the server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await app["bot"].delete_webhook()
            await runner.cleanup()
            
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
