"""Async Redis helpers for application-level caching."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from .config import Config

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None
_redis_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """Return a shared Redis client instance."""
    global _redis_client

    if _redis_client is None:
        async with _redis_lock:
            if _redis_client is None:
                _redis_client = Redis.from_url(
                    Config.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
    return _redis_client


async def close_redis() -> None:
    """Close the shared Redis connection if it exists."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except RedisError as exc:
            logger.debug("Failed to close Redis connection cleanly: %s", exc)
        finally:
            _redis_client = None


async def cache_get_json(key: str) -> Any:
    """Retrieve JSON data from Redis, returning None on cache miss or errors."""
    try:
        client = await get_redis()
        payload = await client.get(key)
    except RedisError as exc:
        logger.debug("Redis get failed for key %s: %s", key, exc)
        return None

    if payload is None:
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("Cached value for key %s is not valid JSON", key)
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Store JSON-serialisable data in Redis."""
    try:
        client = await get_redis()
        payload = json.dumps(value, ensure_ascii=False)
        await client.set(key, payload, ex=ttl_seconds)
    except (TypeError, ValueError):
        logger.warning("Failed to serialise value for cache key %s", key)
    except RedisError as exc:
        logger.debug("Redis set failed for key %s: %s", key, exc)


async def cache_delete(*keys: str) -> None:
    """Remove provided keys from Redis, ignoring missing ones."""
    if not keys:
        return
    try:
        client = await get_redis()
        await client.delete(*keys)
    except RedisError as exc:
        logger.debug("Redis delete failed for keys %s: %s", keys, exc)
