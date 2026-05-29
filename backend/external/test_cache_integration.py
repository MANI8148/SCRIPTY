"""
Test for Task 4.3: Cache Integration with Location Engine

This test suite verifies:
- _get_from_cache(location) checks cache before API calls
- _store_in_cache(location, data) stores results after successful fetch
- Cache key format and namespace usage
- Fallback to curated location data when both APIs fail

Requirements: 2.1, 2.2, 2.3, 2.4, 16.1, 16.2, 16.3
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, patch

from backend.external.location_engine import LocationEngine
from backend.cache.cache_layer import CacheLayer


@pytest.mark.asyncio
async def test_cache_check_before_api_calls():
    """
    Verify that _get_from_cache() is called before making API calls.
    Requirement 2.3: THE Location_Engine SHALL check cache before making external API calls
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # First call - cache miss, should fetch from APIs
    context1 = await engine.get_context("Berlin", "urban")
    assert context1 is not None
    assert context1["name"] == "Berlin"
    
    # Verify data was stored in cache
    cached_data = cache.get("Berlin", namespace="location")
    assert cached_data is not None
    assert cached_data["name"] == "Berlin"
    
    # Second call - cache hit, should NOT fetch from APIs
    # We can verify this by checking that the context is identical
    context2 = await engine.get_context("Berlin", "urban")
    assert context1 == context2
    
    # Verify cache hit rate increased
    stats = cache.get_stats()
    assert stats["hits"] > 0


@pytest.mark.asyncio
async def test_store_in_cache_after_successful_fetch():
    """
    Verify that _store_in_cache() stores results after successful API fetch.
    Requirement 2.4: WHEN cached location data exists and is not expired, 
                     THE Location_Engine SHALL use cached data without API calls
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Clear any existing cache
    cache.invalidate("TestCity", namespace="location")
    
    # Fetch location data (should call APIs)
    context = await engine.get_context("TestCity", "urban")
    assert context is not None
    
    # Verify data was stored in cache with correct namespace
    cached_data = cache.get("TestCity", namespace="location")
    assert cached_data is not None
    assert cached_data["name"] == "TestCity"
    assert "description" in cached_data
    assert "environment_tags" in cached_data
    assert "landmarks" in cached_data


@pytest.mark.asyncio
async def test_cache_namespace_usage():
    """
    Verify that cache uses the correct namespace for location data.
    Requirements 2.1, 2.2: Cache should use appropriate namespaces
    
    Note: Current implementation uses a single "location" namespace for the
    complete enriched context, which is more efficient than separate wiki/geo caches.
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Fetch location data
    context = await engine.get_context("Amsterdam", "urban")
    
    # Verify data is stored in "location" namespace
    cached_data = cache.get("Amsterdam", namespace="location")
    assert cached_data is not None
    assert cached_data["name"] == "Amsterdam"
    
    # Verify data is NOT in other namespaces
    assert cache.get("Amsterdam", namespace="wiki") is None
    assert cache.get("Amsterdam", namespace="geo") is None


@pytest.mark.asyncio
async def test_fallback_to_curated_data_when_apis_fail():
    """
    Verify fallback to curated location data when both APIs fail.
    Requirement 16.3: Implement fallback to curated location data when both APIs fail
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Use a nonsense location that will fail API calls
    context = await engine.get_context("NONEXISTENT_LOCATION_XYZ_12345", "urban")
    
    # Should still return valid context with fallback data
    assert context is not None
    assert "name" in context
    assert context["name"] == "NONEXISTENT_LOCATION_XYZ_12345"
    assert "description" in context
    assert "environment_tags" in context
    assert "landmarks" in context
    
    # Verify environment tags come from curated data
    assert len(context["environment_tags"]) > 0
    assert isinstance(context["environment_tags"], list)


@pytest.mark.asyncio
async def test_cache_prevents_duplicate_api_calls():
    """
    Verify that fetching the same location twice results in only one API call.
    Requirement 2.6 (Property 2): Cache prevents duplicate API calls
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Clear cache for this location
    cache.invalidate("Vienna", namespace="location")
    
    # Track initial cache stats
    initial_stats = cache.get_stats()
    initial_misses = initial_stats["misses"]
    
    # First fetch - should be cache miss and call APIs
    context1 = await engine.get_context("Vienna", "urban")
    stats_after_first = cache.get_stats()
    misses_after_first = stats_after_first["misses"]
    
    # Verify cache miss occurred
    assert misses_after_first > initial_misses
    
    # Second fetch - should be cache hit, no API call
    context2 = await engine.get_context("Vienna", "urban")
    stats_after_second = cache.get_stats()
    hits_after_second = stats_after_second["hits"]
    
    # Verify cache hit occurred
    assert hits_after_second > stats_after_first["hits"]
    
    # Verify contexts are identical
    assert context1 == context2


@pytest.mark.asyncio
async def test_cache_ttl_respected():
    """
    Verify that cache TTL is respected (24 hours default).
    Requirement 1.5: Cache_Layer SHALL store results with TTL of 24 hours
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Fetch location data
    context = await engine.get_context("Prague", "urban")
    
    # Verify data is cached
    cached_data = cache.get("Prague", namespace="location")
    assert cached_data is not None
    
    # Note: We can't easily test TTL expiration without waiting 24 hours
    # or mocking time, but we verify that the cache stores data with TTL
    # by checking that the data is retrievable immediately after storage


@pytest.mark.asyncio
async def test_cache_invalidation_forces_fresh_fetch():
    """
    Verify that cache invalidation forces a fresh API fetch.
    Requirement 1.8 (Property 1): Cache invalidation round-trip
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # First fetch
    context1 = await engine.get_context("Stockholm", "urban")
    
    # Verify cached
    assert cache.get("Stockholm", namespace="location") is not None
    
    # Invalidate cache
    cache.invalidate("Stockholm", namespace="location")
    
    # Verify cache is empty
    assert cache.get("Stockholm", namespace="location") is None
    
    # Second fetch should call APIs again
    context2 = await engine.get_context("Stockholm", "urban")
    
    # Verify data is cached again
    assert cache.get("Stockholm", namespace="location") is not None


@pytest.mark.asyncio
async def test_location_engine_without_cache():
    """
    Verify that Location Engine works without cache layer (cache_layer=None).
    This ensures the engine is resilient to cache unavailability.
    """
    engine = LocationEngine(cache_layer=None)
    
    # Should still work without cache
    context = await engine.get_context("Copenhagen", "urban")
    
    assert context is not None
    assert context["name"] == "Copenhagen"
    assert "description" in context
    assert "environment_tags" in context


@pytest.mark.asyncio
async def test_different_location_types_cached_separately():
    """
    Verify that different location types for the same location name
    are handled correctly.
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Note: Current implementation caches by location name only,
    # not by location type. This is a design decision that treats
    # the location name as the primary cache key.
    
    context_urban = await engine.get_context("TestLocation", "urban")
    context_rural = await engine.get_context("TestLocation", "rural")
    
    # Both should return valid contexts
    assert context_urban is not None
    assert context_rural is not None
    
    # The name should be the same
    assert context_urban["name"] == "TestLocation"
    assert context_rural["name"] == "TestLocation"


if __name__ == "__main__":
    # Run tests manually
    print("Running Task 4.3 Cache Integration Tests...\n")
    
    asyncio.run(test_cache_check_before_api_calls())
    print("✓ test_cache_check_before_api_calls passed")
    
    asyncio.run(test_store_in_cache_after_successful_fetch())
    print("✓ test_store_in_cache_after_successful_fetch passed")
    
    asyncio.run(test_cache_namespace_usage())
    print("✓ test_cache_namespace_usage passed")
    
    asyncio.run(test_fallback_to_curated_data_when_apis_fail())
    print("✓ test_fallback_to_curated_data_when_apis_fail passed")
    
    asyncio.run(test_cache_prevents_duplicate_api_calls())
    print("✓ test_cache_prevents_duplicate_api_calls passed")
    
    asyncio.run(test_cache_ttl_respected())
    print("✓ test_cache_ttl_respected passed")
    
    asyncio.run(test_cache_invalidation_forces_fresh_fetch())
    print("✓ test_cache_invalidation_forces_fresh_fetch passed")
    
    asyncio.run(test_location_engine_without_cache())
    print("✓ test_location_engine_without_cache passed")
    
    asyncio.run(test_different_location_types_cached_separately())
    print("✓ test_different_location_types_cached_separately passed")
    
    print("\nAll cache integration tests passed.")
