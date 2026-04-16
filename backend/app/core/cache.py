"""
AutoOps AI — Redis Cache Manager.

Provides a centralized, async-compatible caching layer over Redis.
All functions fail silently — if Redis is unavailable, the app
falls through to PostgreSQL without crashing.

TTL Constants:
    CTDE_POLICY_TTL     : 10 minutes — policy rules change rarely
    DASHBOARD_TTL       : 60 seconds — stats refresh after each workflow
    GOVERNANCE_TTL      : 5 minutes  — policy table for manager portal
    INSIGHTS_TTL        : 2 minutes  — recent execution insights
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from .config import settings

logger = logging.getLogger("autoops.cache")

# ── TTL Constants (seconds) ──
CTDE_POLICY_TTL = 600       # 10 min
DASHBOARD_TTL = 60          # 1 min
GOVERNANCE_TTL = 300        # 5 min
INSIGHTS_TTL = 120          # 2 min

# ── Singleton Redis client ──
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Return the Redis client, creating it if needed. Returns None on failure."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis_client.ping()
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"⚠️  Redis unavailable — falling back to PostgreSQL: {e}")
            _redis_client = None
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """
    Retrieve a value from Redis cache.
    Returns deserialized Python object, or None on miss/error.
    """
    try:
        client = await get_redis()
        if client is None:
            return None
        raw = await client.get(key)
        if raw is None:
            logger.debug(f"[CACHE MISS] {key}")
            return None
        logger.debug(f"[CACHE HIT]  {key}")
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"[CACHE ERROR] get({key}): {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """
    Serialize and store a value in Redis with a TTL.
    Fails silently if Redis is unavailable.
    """
    try:
        client = await get_redis()
        if client is None:
            return
        serialized = json.dumps(value, default=str)
        await client.setex(key, ttl, serialized)
        logger.info(f"[CACHE SET]  {key} (TTL={ttl}s)")
    except Exception as e:
        logger.warning(f"[CACHE ERROR] set({key}): {e}")


async def cache_delete(key: str) -> None:
    """Evict a single key from Redis cache."""
    try:
        client = await get_redis()
        if client is None:
            return
        await client.delete(key)
        logger.info(f"[CACHE INVALIDATED] {key}")
    except Exception as e:
        logger.warning(f"[CACHE ERROR] delete({key}): {e}")


async def cache_delete_pattern(pattern: str) -> None:
    """Evict all keys matching a wildcard pattern (e.g. 'ctde:*')."""
    try:
        client = await get_redis()
        if client is None:
            return
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
            logger.info(f"[CACHE INVALIDATED] pattern={pattern} ({len(keys)} keys)")
    except Exception as e:
        logger.warning(f"[CACHE ERROR] delete_pattern({pattern}): {e}")


# ── Namespaced Key Builders ──
def key_ctde_policy(agent_role: str) -> str:
    return f"ctde:{agent_role}"

def key_dashboard(user_id: int) -> str:
    return f"dashboard:{user_id}"

def key_governance_policies() -> str:
    return "governance:policies"

def key_governance_insights() -> str:
    return "governance:insights"
