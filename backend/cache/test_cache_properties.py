"""
Property-based tests for CacheLayer (Tasks 2.4 and 2.5)

Tests cover:
- Property 1: Cache invalidation round-trip
  Validates: Requirements 1.8
  For any location name, if data is cached, then invalidated, then retrieved
  again, the result should be None (cache miss).

- Property 2: Cache prevents duplicate API calls
  Validates: Requirements 2.6
  For any location name, fetching location data twice within the TTL period
  SHALL result in exactly one external API call, with the second fetch
  returning cached data.
"""
import unittest
from unittest.mock import MagicMock, call, patch

from hypothesis import given, settings
from hypothesis import strategies as st


def _make_cache():
    """Return a CacheLayer backed only by in-memory storage (no Redis needed)."""
    with patch("backend.cache.cache_layer.CacheLayer._connect_redis"):
        from backend.cache.cache_layer import CacheLayer

        cache = CacheLayer(redis_url="redis://localhost:9999/0", fallback_to_memory=True)
        cache._redis_available = False
        cache._redis = None
        return cache


class TestCacheInvalidationRoundTrip(unittest.TestCase):
    """
    Property 1: Cache invalidation round-trip

    Validates: Requirements 1.8

    FOR ALL cached location data, retrieving then invalidating then retrieving
    SHALL result in a fresh API call (cache miss), i.e. the second retrieval
    returns None.
    """

    @given(
        location=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters=" -_",
            ),
            min_size=1,
            max_size=100,
        ),
        namespace=st.sampled_from(["wiki", "geo", "entities", "default"]),
        value=st.one_of(
            st.text(min_size=1, max_size=200),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=50),
                min_size=1,
                max_size=5,
            ),
            st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10),
        ),
    )
    @settings(max_examples=20)
    def test_retrieve_invalidate_retrieve_is_cache_miss(self, location, namespace, value):
        """
        **Validates: Requirements 1.8**

        Property: For any location name and any cacheable value, the sequence:
          1. set(location, value)
          2. get(location)  → must return the cached value (not None)
          3. invalidate(location)
          4. get(location)  → must return None (cache miss)
        """
        cache = _make_cache()

        # Step 1: Store the value in the cache
        stored = cache.set(location, value, ttl_hours=24, namespace=namespace)
        self.assertTrue(stored, "set() should return True when storing a value")

        # Step 2: Verify the value is retrievable (cache hit)
        retrieved = cache.get(location, namespace=namespace)
        self.assertEqual(
            retrieved,
            value,
            f"get() after set() should return the cached value for location={location!r}",
        )

        # Step 3: Invalidate the cache entry
        cache.invalidate(location, namespace=namespace)

        # Step 4: Verify the value is no longer in the cache (cache miss)
        after_invalidation = cache.get(location, namespace=namespace)
        self.assertIsNone(
            after_invalidation,
            f"get() after invalidate() should return None for location={location!r}, "
            f"namespace={namespace!r}",
        )


class TestCacheIdempotence(unittest.TestCase):
    """
    Property 2: Cache prevents duplicate API calls

    **Validates: Requirements 2.6**

    FOR ALL location names, fetching location data twice within the TTL period
    SHALL result in exactly one external API call, with the second fetch
    returning cached data.

    The test simulates a "location fetch" function that:
      1. Checks the cache for the location.
      2. On a cache miss, calls the external API (tracked via a mock counter)
         and stores the result in the cache.
      3. On a cache hit, returns the cached value without calling the API.

    After two fetches for the same location, the API call counter MUST equal 1.
    """

    @given(
        location=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters=" -_",
            ),
            min_size=1,
            max_size=100,
        ),
        namespace=st.sampled_from(["wiki", "geo", "entities", "default"]),
        api_response=st.one_of(
            st.text(min_size=1, max_size=200),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.text(min_size=1, max_size=50),
                min_size=1,
                max_size=5,
            ),
            st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10),
        ),
    )
    @settings(max_examples=20)
    def test_second_fetch_uses_cache_not_api(self, location, namespace, api_response):
        """
        **Validates: Requirements 2.6**

        Property: For any location name, the sequence:
          1. fetch_location(location)  → cache miss → calls API once, stores result
          2. fetch_location(location)  → cache hit  → returns cached data, no API call

        After both fetches, the mock API MUST have been called exactly once.
        """
        cache = _make_cache()

        # Mock API call counter – simulates an external service (Wikipedia/Nominatim)
        mock_api = MagicMock(return_value=api_response)

        def fetch_location(loc: str):
            """Simulate a location-engine fetch: cache-first, API on miss."""
            cached = cache.get(loc, namespace=namespace)
            if cached is not None:
                return cached
            # Cache miss: call the external API and store the result
            result = mock_api(loc)
            cache.set(loc, result, ttl_hours=24, namespace=namespace)
            return result

        # --- First fetch: should call the API and populate the cache ---
        first_result = fetch_location(location)
        self.assertEqual(
            first_result,
            api_response,
            f"First fetch should return the API response for location={location!r}",
        )
        self.assertEqual(
            mock_api.call_count,
            1,
            f"API should be called exactly once after first fetch for location={location!r}",
        )

        # --- Second fetch: should return cached data WITHOUT calling the API again ---
        second_result = fetch_location(location)
        self.assertEqual(
            second_result,
            api_response,
            f"Second fetch should return the same value as the first for location={location!r}",
        )
        self.assertEqual(
            mock_api.call_count,
            1,
            f"API should still have been called exactly once after second fetch "
            f"for location={location!r} (second fetch must use cache)",
        )

        # Confirm both fetches returned identical data
        self.assertEqual(
            first_result,
            second_result,
            f"Both fetches must return identical data for location={location!r}",
        )


if __name__ == "__main__":
    unittest.main()
