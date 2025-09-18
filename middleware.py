import logging
import time
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging incoming updates."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process the event and log information."""
        start_time = time.time()
        
        # Log incoming update
        if isinstance(event, Message):
            user = event.from_user
            logger.info(
                f"Received message from user {user.id} (@{user.username}): "
                f"'{event.text[:50]}{'...' if len(event.text or '') > 50 else ''}'"
            )
        
        try:
            # Call the next handler
            result = await handler(event, data)
            
            # Log successful processing
            processing_time = time.time() - start_time
            logger.debug(f"Update processed successfully in {processing_time:.3f}s")
            
            return result
            
        except Exception as e:
            # Log error
            processing_time = time.time() - start_time
            logger.error(f"Error processing update: {e} (took {processing_time:.3f}s)")
            raise


class UserMiddleware(BaseMiddleware):
    """Middleware for user validation and data enrichment."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process the event and validate user."""
        # Add user validation logic here if needed
        # For example, check if user is banned, blocked, etc.
        
        # Extract user information
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
            
            # Add user info to data for handlers to use
            data['user'] = user
            data['user_id'] = user.id
            data['username'] = user.username
            data['is_bot'] = user.is_bot
            
            # Log user activity
            logger.debug(f"Processing update for user {user.id} (@{user.username})")
        
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, max_requests: int = 30, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests = {}  # {user_id: [timestamps]}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Check rate limits for the user."""
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)
        
        user_id = event.from_user.id
        current_time = time.time()
        
        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < self.time_window
            ]
        else:
            self.user_requests[user_id] = []
        
        # Check rate limit
        if len(self.user_requests[user_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            await event.answer(
                "⚠️ Too many requests! Please slow down and try again later.",
                show_alert=True
            )
            return
        
        # Add current request
        self.user_requests[user_id].append(current_time)
        
        return await handler(event, data)


def register_middleware(dp):
    """Register all middleware with the dispatcher."""
    # Add middleware in order (last added is called first)
    dp.message.middleware(RateLimitMiddleware(max_requests=30, time_window=60))
    dp.message.middleware(UserMiddleware())
    dp.message.middleware(LoggingMiddleware())
    
    # Register for all update types if needed
    dp.update.middleware(LoggingMiddleware())
    
    logger.info("All middleware registered successfully")
