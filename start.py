#!/usr/bin/env python3
"""
Startup script for the Telegram bot.
This script handles environment setup and bot initialization.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load environment variables from .env file if it exists
env_file = current_dir / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"Loaded environment variables from {env_file}")
else:
    print("No .env file found. Using system environment variables.")

# Import and run the bot
if __name__ == "__main__":
    try:
        from app.bot import main
        import asyncio
        
        print("Starting Telegram bot...")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)
