"""
Cache service — typed wrappers around Redis operations.

Every function receives a `Redis` client as its first argument.
The client is injected via ``get_redis()`` from ``app.utils.deps``;
this module never creates its own connection.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


# ── Basic get / set / delete ──────────────────────────────────


async def get(redis: Redis, key: str) -> str | None:
    """Get a string value by key.  Returns ``None`` on cache miss."""
    return await redis.get(key)


async def get_json(redis: Redis, key: str) -> Any | None:
    """Get and JSON-decode a value.  Returns ``None`` on cache miss."""
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set(
    redis: Redis,
    key: str,
    value: str | int | float,
    ttl: int | None = None,
) -> None:
    """Set a string/numeric value with an optional TTL (seconds)."""
    if ttl is not None:
        await redis.set(key, value, ex=ttl)
    else:
        await redis.set(key, value)


async def set_json(
    redis: Redis,
    key: str,
    value: Any,
    ttl: int | None = None,
) -> None:
    """JSON-encode and store a value with an optional TTL (seconds)."""
    payload = json.dumps(value, default=str)
    await set(redis, key, payload, ttl=ttl)


async def delete(redis: Redis, key: str) -> None:
    """Delete a key.  No-op if it doesn't exist."""
    await redis.delete(key)


async def delete_pattern(redis: Redis, pattern: str) -> int:
    """Delete all keys matching a glob pattern.  Returns count deleted."""
    cursor, count = b"0", 0
    while cursor:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            count += await redis.delete(*keys)
    return count


# ── Pub / Sub ─────────────────────────────────────────────────


async def publish(redis: Redis, channel: str, message: Any) -> int:
    """
    Publish a message to a Redis Pub/Sub channel.

    *message* is JSON-encoded if it isn't already a string.
    Returns the number of subscribers that received the message.
    """
    payload = message if isinstance(message, str) else json.dumps(message, default=str)
    return await redis.publish(channel, payload)


# ── Sorted-set helpers (leaderboard) ─────────────────────────


async def zadd(redis: Redis, key: str, member: str, score: float) -> None:
    """Add or update a member's score in a sorted set."""
    await redis.zadd(key, {member: score})


async def zincrby(redis: Redis, key: str, member: str, increment: float) -> float:
    """Increment a member's score in a sorted set.  Returns new score."""
    return await redis.zincrby(key, increment, member)


async def zrevrank(redis: Redis, key: str, member: str) -> int | None:
    """
    Get the 0-based rank of *member* in a sorted set (highest score = rank 0).
    Returns ``None`` if the member doesn't exist.
    """
    return await redis.zrevrank(key, member)


async def zscore(redis: Redis, key: str, member: str) -> float | None:
    """Get the score of *member* in a sorted set.  ``None`` if absent."""
    return await redis.zscore(key, member)


async def zrevrange_with_scores(
    redis: Redis,
    key: str,
    start: int = 0,
    stop: int = -1,
) -> list[tuple[str, float]]:
    """
    Return members + scores from a sorted set, highest-score first.

    Default returns the entire set.  Use *start*/*stop* for pagination
    (e.g. ``start=0, stop=9`` for top 10).
    """
    return await redis.zrevrange(key, start, stop, withscores=True)


async def zcard(redis: Redis, key: str) -> int:
    """Return the number of members in a sorted set."""
    return await redis.zcard(key)


# ── Counter helpers ───────────────────────────────────────────


async def incr(redis: Redis, key: str, amount: int = 1) -> int:
    """Increment a counter key by *amount*.  Creates the key if missing."""
    return await redis.incrby(key, amount)


async def decr(redis: Redis, key: str, amount: int = 1) -> int:
    """Decrement a counter key by *amount*.  Creates the key if missing."""
    return await redis.decrby(key, amount)


async def get_int(redis: Redis, key: str) -> int | None:
    """Get a key's value as an integer.  ``None`` on miss."""
    val = await redis.get(key)
    return int(val) if val is not None else None
