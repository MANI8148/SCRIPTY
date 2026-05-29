"""
SCRIPTY - Cache Layer
Multi-tier caching system using Redis as primary cache with in-memory dictionary fallback.

Implements:
- Redis connection with connection pooling (5-20 connections)
- Retry logic with exponential backoff (3 retries: 100ms, 200ms, 400ms)
- Automatic fallback to in-memory cache when Redis is unavailable
- Namespace isolation for wiki, geo, and entity data
"""
import json
import time
import threading
from typing import Any, Optional

from backend.config import Config
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_RETRY_BACKOFF_MS = [100, 200, 400]  # milliseconds

# Connection pool configuration
_POOL_MIN_CONNECTIONS = 5
_POOL_MAX_CONNECTIONS = 20


def _build_namespaced_key(key: str, namespace: str) -> str:
    """Build a namespaced Redis key to prevent collisions between namespaces."""
    return f"{namespace}:{key}"


class CacheLayer:
    """
    Multi-tier cache providing Redis-backed distributed caching with automatic
    in-memory fallback when Redis is unavailable.

    Redis is the primary store; the in-memory dict is used when Redis is down
    or when a Redis operation fails after all retries.

    Requirements: 1.1, 1.2, 20.1, 20.3
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        fallback_to_memory: bool = True,
    ) -> None:
        """
        Initialize the cache layer.

        Args:
            redis_url: Redis connection URL.  Defaults to Config.REDIS_URL.
            fallback_to_memory: When True, fall back to in-memory cache if
                Redis is unavailable.  Defaults to True.
        """
        self._redis_url: str = redis_url or Config.REDIS_URL
        self._fallback_to_memory: bool = fallback_to_memory

        # In-memory fallback store: {namespaced_key: {"value": ..., "expires_at": float}}
        self._memory_cache: dict[str, dict] = {}
        self._memory_lock = threading.Lock()

        # Redis client (None when unavailable)
        self._redis = None
        self._redis_available: bool = False

        # Statistics
        self._hits: int = 0
        self._misses: int = 0
        self._redis_errors: int = 0

        # Attempt initial Redis connection
        self._connect_redis()

    # ------------------------------------------------------------------
    # Redis connection management
    # ------------------------------------------------------------------

    def _connect_redis(self) -> None:
        """
        Attempt to connect to Redis using a connection pool.

        On success, sets self._redis and self._redis_available = True.
        On failure, logs a warning and leaves self._redis_available = False
        so that the in-memory fallback is used.
        """
        try:
            import redis  # type: ignore

            pool = redis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=_POOL_MAX_CONNECTIONS,
                decode_responses=True,
            )
            client = redis.Redis(connection_pool=pool)
            # Verify connectivity with a lightweight PING
            client.ping()
            self._redis = client
            self._redis_available = True
            logger.info(
                "Redis connected",
                extra={"extra_fields": {"redis_url": self._redis_url}},
            )
        except Exception as exc:  # noqa: BLE001
            self._redis = None
            self._redis_available = False
            logger.warning(
                "Redis unavailable, falling back to in-memory cache: %s", exc
            )

    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute a Redis operation with up to _MAX_RETRIES retries and
        exponential backoff.

        Args:
            operation: Callable that performs the Redis operation.
            *args / **kwargs: Forwarded to *operation*.

        Returns:
            The return value of *operation* on success, or None on failure.

        Raises:
            Nothing – failures are logged and None is returned so callers can
            fall back to the in-memory cache.
        """
        last_exc = None
        for attempt in range(_MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._redis_errors += 1
                if attempt < _MAX_RETRIES - 1:
                    backoff_s = _RETRY_BACKOFF_MS[attempt] / 1000.0
                    logger.warning(
                        "Redis operation failed (attempt %d/%d), retrying in %.0fms: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        _RETRY_BACKOFF_MS[attempt],
                        exc,
                    )
                    time.sleep(backoff_s)

        # All retries exhausted
        logger.error(
            "Redis operation failed after %d retries: %s", _MAX_RETRIES, last_exc
        )
        self._redis_available = False
        return None

    # ------------------------------------------------------------------
    # In-memory cache helpers
    # ------------------------------------------------------------------

    def _memory_get(self, namespaced_key: str) -> Optional[Any]:
        """Retrieve a value from the in-memory cache, respecting TTL."""
        with self._memory_lock:
            entry = self._memory_cache.get(namespaced_key)
            if entry is None:
                return None
            if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
                del self._memory_cache[namespaced_key]
                return None
            return entry["value"]

    def _memory_set(
        self, namespaced_key: str, value: Any, ttl_hours: int = 24
    ) -> None:
        """Store a value in the in-memory cache with an optional TTL."""
        expires_at = time.time() + ttl_hours * 3600 if ttl_hours > 0 else None
        with self._memory_lock:
            self._memory_cache[namespaced_key] = {
                "value": value,
                "expires_at": expires_at,
            }

    def _memory_delete(self, namespaced_key: str) -> bool:
        """Remove a key from the in-memory cache. Returns True if key existed."""
        with self._memory_lock:
            return self._memory_cache.pop(namespaced_key, None) is not None

    def _memory_delete_pattern(self, pattern: str) -> int:
        """
        Remove all in-memory keys whose namespaced key starts with *pattern*.
        Returns the number of keys removed.
        """
        import fnmatch

        with self._memory_lock:
            matching = [k for k in self._memory_cache if fnmatch.fnmatch(k, pattern)]
            for k in matching:
                del self._memory_cache[k]
            return len(matching)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Checks Redis first; falls back to in-memory cache if Redis is
        unavailable or the key is not found in Redis.

        Args:
            key: Cache key (without namespace prefix).
            namespace: Logical namespace (e.g. "wiki", "geo", "entities").

        Returns:
            Cached value, or None on cache miss.
        """
        namespaced_key = _build_namespaced_key(key, namespace)

        # --- Try Redis ---
        if self._redis_available and self._redis is not None:
            raw = self._execute_with_retry(self._redis.get, namespaced_key)
            if raw is not None:
                try:
                    value = json.loads(raw)
                    self._hits += 1
                    logger.debug(
                        "Cache hit (Redis)",
                        extra={
                            "cache_key": namespaced_key,
                            "cache_operation": "get",
                        },
                    )
                    return value
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning(
                        "Failed to deserialize cached value for key %s: %s",
                        namespaced_key,
                        exc,
                    )

        # --- Try in-memory fallback ---
        if self._fallback_to_memory:
            value = self._memory_get(namespaced_key)
            if value is not None:
                self._hits += 1
                logger.debug(
                    "Cache hit (memory)",
                    extra={
                        "cache_key": namespaced_key,
                        "cache_operation": "get",
                    },
                )
                return value

        self._misses += 1
        logger.debug(
            "Cache miss",
            extra={
                "cache_key": namespaced_key,
                "cache_operation": "get",
            },
        )
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_hours: int = 24,
        namespace: str = "default",
    ) -> bool:
        """
        Store a value in the cache with a TTL.

        Writes to Redis when available; always writes to the in-memory cache
        as a warm copy so that a Redis failure does not cause an immediate miss.

        Args:
            key: Cache key (without namespace prefix).
            value: Value to cache (must be JSON-serialisable).
            ttl_hours: Time-to-live in hours.  Defaults to 24.
            namespace: Logical namespace.

        Returns:
            True if the value was stored in at least one tier.
        """
        namespaced_key = _build_namespaced_key(key, namespace)
        ttl_seconds = ttl_hours * 3600

        try:
            serialized = json.dumps(value)
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize value for key %s: %s", namespaced_key, exc
            )
            return False

        stored = False

        # --- Write to Redis ---
        if self._redis_available and self._redis is not None:
            result = self._execute_with_retry(
                self._redis.setex, namespaced_key, ttl_seconds, serialized
            )
            if result is not None:
                stored = True
                logger.debug(
                    "Cache set (Redis)",
                    extra={
                        "cache_key": namespaced_key,
                        "cache_operation": "set",
                    },
                )

        # --- Write to in-memory fallback ---
        if self._fallback_to_memory:
            self._memory_set(namespaced_key, value, ttl_hours)
            stored = True
            logger.debug(
                "Cache set (memory)",
                extra={
                    "cache_key": namespaced_key,
                    "cache_operation": "set",
                },
            )

        return stored

    def invalidate(self, key: str, namespace: str = "default") -> bool:
        """
        Remove a specific key from the cache (both Redis and in-memory).

        Args:
            key: Cache key (without namespace prefix).
            namespace: Logical namespace.

        Returns:
            True if the key was found and removed from at least one tier.
        """
        namespaced_key = _build_namespaced_key(key, namespace)
        removed = False

        if self._redis_available and self._redis is not None:
            result = self._execute_with_retry(self._redis.delete, namespaced_key)
            if result:
                removed = True

        if self._fallback_to_memory:
            if self._memory_delete(namespaced_key):
                removed = True

        logger.debug(
            "Cache invalidate",
            extra={
                "cache_key": namespaced_key,
                "cache_operation": "invalidate",
            },
        )
        return removed

    def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """
        Remove all keys matching a glob pattern within a namespace.

        Args:
            pattern: Glob pattern applied to the key portion (before namespace
                prefix is added).  E.g. "london*" removes all keys starting
                with "london" in the given namespace.
            namespace: Logical namespace.

        Returns:
            Total number of keys removed across both tiers.
        """
        namespaced_pattern = _build_namespaced_key(pattern, namespace)
        removed = 0

        if self._redis_available and self._redis is not None:
            try:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(
                        cursor=cursor, match=namespaced_pattern, count=100
                    )
                    if keys:
                        deleted = self._execute_with_retry(self._redis.delete, *keys)
                        if deleted:
                            removed += deleted
                    if cursor == 0:
                        break
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis SCAN failed during invalidate_pattern: %s", exc)

        if self._fallback_to_memory:
            removed += self._memory_delete_pattern(namespaced_pattern)

        logger.debug(
            "Cache invalidate_pattern: removed %d keys matching %s",
            removed,
            namespaced_pattern,
        )
        return removed

    def get_stats(self) -> dict:
        """
        Return cache statistics.

        Returns:
            Dictionary with keys: hits, misses, hit_rate, redis_available,
            redis_errors, memory_key_count.
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        with self._memory_lock:
            memory_key_count = len(self._memory_cache)

        redis_key_count: Optional[int] = None
        if self._redis_available and self._redis is not None:
            try:
                redis_key_count = self._redis.dbsize()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to get Redis dbsize: %s", exc)

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "redis_available": self._redis_available,
            "redis_errors": self._redis_errors,
            "memory_key_count": memory_key_count,
            "redis_key_count": redis_key_count,
        }

    @property
    def is_redis_available(self) -> bool:
        """True when the Redis connection is healthy."""
        return self._redis_available
