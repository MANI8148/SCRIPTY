"""
Unit tests for CacheLayer (Task 2.1)

Tests cover:
- Initialization with and without Redis
- In-memory fallback when Redis is unavailable
- Retry logic with exponential backoff
- get / set / invalidate / invalidate_pattern operations
- Namespace isolation
- Statistics tracking
"""
import time
import unittest
from unittest.mock import MagicMock, patch, call


class TestCacheLayerInit(unittest.TestCase):
    """Tests for CacheLayer.__init__ and Redis connection setup."""

    def test_init_falls_back_to_memory_when_redis_unavailable(self):
        """When Redis is not reachable, the layer should still initialise."""
        with patch("backend.cache.cache_layer.Config") as mock_cfg:
            mock_cfg.REDIS_URL = "redis://localhost:6379/0"
            # Simulate redis import failure
            with patch.dict("sys.modules", {"redis": None}):
                from backend.cache.cache_layer import CacheLayer
                cache = CacheLayer(redis_url="redis://localhost:9999/0")
                self.assertFalse(cache.is_redis_available)

    def test_init_with_redis_available(self):
        """When Redis responds to PING, redis_available should be True."""
        mock_redis_module = MagicMock()
        mock_pool = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_module.ConnectionPool.from_url.return_value = mock_pool
        mock_redis_module.Redis.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            # Re-import to pick up patched module
            import importlib
            import backend.cache.cache_layer as mod
            importlib.reload(mod)
            cache = mod.CacheLayer(redis_url="redis://localhost:6379/0")
            self.assertTrue(cache.is_redis_available)

    def test_connection_pool_max_connections(self):
        """Connection pool should be created with max 20 connections."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_module.Redis.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            import importlib
            import backend.cache.cache_layer as mod
            importlib.reload(mod)
            mod.CacheLayer(redis_url="redis://localhost:6379/0")
            mock_redis_module.ConnectionPool.from_url.assert_called_once()
            _, kwargs = mock_redis_module.ConnectionPool.from_url.call_args
            self.assertEqual(kwargs.get("max_connections"), 20)


class TestCacheLayerMemoryFallback(unittest.TestCase):
    """Tests for in-memory cache operations when Redis is unavailable."""

    def _make_cache(self):
        """Return a CacheLayer with Redis disabled."""
        with patch("backend.cache.cache_layer.CacheLayer._connect_redis"):
            from backend.cache.cache_layer import CacheLayer
            cache = CacheLayer(redis_url="redis://localhost:9999/0")
            cache._redis_available = False
            cache._redis = None
            return cache

    def test_set_and_get_memory(self):
        cache = self._make_cache()
        cache.set("city", {"name": "Mumbai"}, ttl_hours=1, namespace="wiki")
        result = cache.get("city", namespace="wiki")
        self.assertEqual(result, {"name": "Mumbai"})

    def test_get_returns_none_on_miss(self):
        cache = self._make_cache()
        result = cache.get("nonexistent", namespace="wiki")
        self.assertIsNone(result)

    def test_invalidate_removes_key(self):
        cache = self._make_cache()
        cache.set("city", "Delhi", namespace="geo")
        cache.invalidate("city", namespace="geo")
        self.assertIsNone(cache.get("city", namespace="geo"))

    def test_invalidate_pattern_removes_matching_keys(self):
        cache = self._make_cache()
        cache.set("london_wiki", "data1", namespace="wiki")
        cache.set("london_geo", "data2", namespace="wiki")
        cache.set("paris_wiki", "data3", namespace="wiki")
        removed = cache.invalidate_pattern("london*", namespace="wiki")
        self.assertEqual(removed, 2)
        self.assertIsNone(cache.get("london_wiki", namespace="wiki"))
        self.assertIsNone(cache.get("london_geo", namespace="wiki"))
        self.assertIsNotNone(cache.get("paris_wiki", namespace="wiki"))

    def test_namespace_isolation(self):
        """Same key in different namespaces should not collide."""
        cache = self._make_cache()
        cache.set("london", "wiki_data", namespace="wiki")
        cache.set("london", "geo_data", namespace="geo")
        self.assertEqual(cache.get("london", namespace="wiki"), "wiki_data")
        self.assertEqual(cache.get("london", namespace="geo"), "geo_data")

    def test_ttl_expiry(self):
        """Entries should expire after their TTL."""
        cache = self._make_cache()
        # Use a very small TTL by directly manipulating the internal store
        cache.set("temp", "value", ttl_hours=1, namespace="test")
        # Manually expire the entry
        key = "test:temp"
        with cache._memory_lock:
            cache._memory_cache[key]["expires_at"] = time.time() - 1
        self.assertIsNone(cache.get("temp", namespace="test"))

    def test_stats_hit_rate(self):
        cache = self._make_cache()
        cache.set("k", "v", namespace="ns")
        cache.get("k", namespace="ns")   # hit
        cache.get("missing", namespace="ns")  # miss
        stats = cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertAlmostEqual(stats["hit_rate"], 0.5)

    def test_set_returns_true_with_memory_fallback(self):
        cache = self._make_cache()
        result = cache.set("k", "v", namespace="ns")
        self.assertTrue(result)

    def test_set_returns_false_for_non_serializable_value(self):
        cache = self._make_cache()
        result = cache.set("k", object(), namespace="ns")
        self.assertFalse(result)


class TestCacheLayerRetryLogic(unittest.TestCase):
    """Tests for Redis retry logic with exponential backoff."""

    def test_retry_called_three_times_on_failure(self):
        """_execute_with_retry should attempt the operation 3 times."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_module.Redis.return_value = mock_client
        mock_redis_module.ConnectionPool.from_url.return_value = MagicMock()

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            import importlib
            import backend.cache.cache_layer as mod
            importlib.reload(mod)
            cache = mod.CacheLayer(redis_url="redis://localhost:6379/0")

        failing_op = MagicMock(side_effect=Exception("connection error"))

        with patch("time.sleep"):  # Don't actually sleep in tests
            result = cache._execute_with_retry(failing_op)

        self.assertIsNone(result)
        self.assertEqual(failing_op.call_count, 3)

    def test_retry_succeeds_on_second_attempt(self):
        """_execute_with_retry should return the result on the first success."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_module.Redis.return_value = mock_client
        mock_redis_module.ConnectionPool.from_url.return_value = MagicMock()

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            import importlib
            import backend.cache.cache_layer as mod
            importlib.reload(mod)
            cache = mod.CacheLayer(redis_url="redis://localhost:6379/0")

        op = MagicMock(side_effect=[Exception("fail"), "success"])

        with patch("time.sleep"):
            result = cache._execute_with_retry(op)

        self.assertEqual(result, "success")
        self.assertEqual(op.call_count, 2)

    def test_backoff_delays_are_applied(self):
        """Exponential backoff delays should be 100ms and 200ms between retries."""
        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_module.Redis.return_value = mock_client
        mock_redis_module.ConnectionPool.from_url.return_value = MagicMock()

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            import importlib
            import backend.cache.cache_layer as mod
            importlib.reload(mod)
            cache = mod.CacheLayer(redis_url="redis://localhost:6379/0")

        failing_op = MagicMock(side_effect=Exception("fail"))

        with patch("time.sleep") as mock_sleep:
            cache._execute_with_retry(failing_op)

        # Should sleep twice (after attempt 1 and attempt 2; not after final attempt)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(0.1)   # 100ms
        mock_sleep.assert_any_call(0.2)   # 200ms


if __name__ == "__main__":
    unittest.main()
