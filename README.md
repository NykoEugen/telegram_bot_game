# Telegram Bot Game - Base Skeleton

A modern Telegram bot skeleton built with aiogram 3.13, featuring webhook support, PostgreSQL persistence managed through Alembic migrations, Redis-backed caching, and an async-first architecture. This skeleton is designed to be a starting point for building Telegram games and interactive bots.

## Features

- 🤖 **aiogram 3.13** - Modern async Telegram Bot API framework
- 🔗 **Webhook Support** - Efficient webhook-based updates instead of polling
- 🗄️ **PostgreSQL + Alembic** - Production-ready database with versioned migrations
- 🧠 **Redis Caching** - Shared cache layer for expensive lookups
- ⚡ **Async/Await** - Fully asynchronous architecture for better performance
- 🛡️ **Middleware** - Logging, rate limiting, and user validation
- 🚀 **ngrok Integration** - Easy local development with ngrok tunneling
- 📝 **Comprehensive Logging** - Detailed logging for debugging and monitoring

## Project Structure

```
telegram_bot_game/
├── app/
│   ├── __init__.py
│   ├── bot.py                 # Webhook entrypoint and aiohttp app
│   ├── config.py              # Settings loading and validation
│   ├── database.py            # SQLAlchemy models and async helpers
│   ├── keyboards.py           # Inline keyboard builders
│   ├── middleware.py          # Global aiogram middleware
│   ├── core/                  # Combat, hero, monster & encounter systems
│   ├── handlers/              # Aiogram routers grouped by domain
│   ├── initializers/          # Database seeding utilities
│   └── data/                  # JSON content for quests/classes
├── docs/                      # Design notes and configuration guides
├── tests/                     # Utility scripts for manual verification
├── start.py                   # Startup helper that loads .env and runs the bot
├── requirements.txt           # Python dependencies
├── env.template               # Environment variables template
└── README.md                  # This file
```

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose (recommended) **or** Python 3.11+, PostgreSQL 15+, and Redis 7+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- ngrok (for webhook development)

### 2. Configuration

```bash
cp env.template .env
# Edit .env to provide BOT_TOKEN, webhook settings, and optional DB credentials
```

If you plan to run the stack with Docker Compose, the defaults in `env.template` match the service hostnames (`postgres`, `redis`). For local execution point the URLs at your own installations.

### 3. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

The application waits for PostgreSQL, runs `alembic upgrade head`, and then starts the webhook server. Redis caching is enabled automatically.

### 4. Manual setup (optional)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Ensure PostgreSQL & Redis are running and DATABASE_URL / REDIS_URL are configured
alembic upgrade head
python start.py
```

### 5. Setup ngrok (for webhook testing)

```bash
ngrok http 8080
# Update WEBHOOK_DOMAIN in .env with the forwarded HTTPS host
```

## Available Commands

Once the bot is running, users can interact with these commands:

- `/start` - Start the bot and register user
- `/help` - Show available commands
- `/info` - Display user information
- `/ping` - Test bot responsiveness
- `/time` - Show current time
- `/bounties` - Browse procedurally generated repeatable missions

## Database Schema

The bot includes a basic user management system:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,        -- Telegram user ID
    username TEXT,                 -- Telegram username
    first_name TEXT,               -- User's first name
    last_name TEXT,                -- User's last name
    is_bot BOOLEAN DEFAULT FALSE,  -- Whether user is a bot
    language_code TEXT,            -- User's language preference
    created_at TEXT NOT NULL       -- Registration timestamp
);
```

## Development

### Adding New Commands

1. Create a new handler in `handlers.py`:

```python
@router.message(Command("mycommand"))
async def cmd_mycommand(message: Message):
    """Handle /mycommand."""
    await message.answer("Hello from my command!")
```

2. Register the handler by including it in the router.

### Adding Database Models

1. Define new models in `database.py`:

```python
class GameScore(Base):
    __tablename__ = "game_scores"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    score: Mapped[int] = mapped_column(default=0)
    game_type: Mapped[str] = mapped_column(nullable=False)
```

2. The database will automatically create tables on startup.

### Custom Middleware

Add custom middleware in `middleware.py`:

```python
class CustomMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Your middleware logic here
        return await handler(event, data)
```

## Production Deployment

For production deployment:

1. **Use a proper web server** (nginx, Apache) as a reverse proxy
2. **Provision managed PostgreSQL** with backups and connection pooling
3. **Set up proper logging** with log rotation
4. **Use environment variables** for all sensitive configuration
5. **Enable SSL/TLS** for webhook endpoints
6. **Set up monitoring** and health checks

### Environment Variables for Production

```bash
# Production configuration
BOT_TOKEN=your_production_bot_token
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
WEBHOOK_DOMAIN=your-production-domain.com
WEBHOOK_SECRET=strong_secret_token
DATABASE_URL=postgresql://user:password@localhost/bot_db
LOG_LEVEL=WARNING
```

## Troubleshooting

### Common Issues

1. **"BOT_TOKEN environment variable is required"**
   - Make sure your `.env` file contains a valid `BOT_TOKEN`
   - Verify the token is correct and the bot is not banned

2. **"WEBHOOK_DOMAIN environment variable must be set"**
   - Update `WEBHOOK_DOMAIN` in your `.env` file with your ngrok domain
   - Ensure the domain is accessible via HTTPS

3. **Database errors**
   - Confirm PostgreSQL is running and credentials in `DATABASE_URL` are correct
   - Run `alembic upgrade head` to apply pending migrations

4. **ngrok connection issues**
   - Verify ngrok is running and accessible
   - Check firewall settings
   - Ensure the tunnel is using HTTPS

### Logs

The bot provides comprehensive logging:
- **INFO**: General bot operations and user interactions
- **DEBUG**: Detailed processing information
- **ERROR**: Error conditions and exceptions
- **WARNING**: Rate limiting and other warnings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions and support:
- Check the [aiogram documentation](https://docs.aiogram.dev/)
- Review the [Telegram Bot API documentation](https://core.telegram.org/bots/api)
- Open an issue in this repository
## Content Initializers

For quest lines and repeatable content, run the following helpers after applying migrations:

```bash
python -m app.initializers.graph_quests   # syncs graph quest data from JSON
python -m app.initializers.bounties       # seeds bounty templates used by /bounties
```
