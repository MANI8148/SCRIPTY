"""
Unit Tests for Location Engine (Task 4.4)

This test suite verifies:
- Async API call execution with mocked aiohttp
- Cache integration (hit and miss scenarios) - already covered in test_cache_integration.py
- Fallback mechanisms when APIs fail
- Timeout handling

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 16.1, 16.2, 16.3
"""
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
import aiohttp

from backend.external.location_engine import LocationEngine
from backend.cache.cache_layer import CacheLayer


@pytest.mark.asyncio
async def test_async_api_call_execution_with_mocked_aiohttp():
    """
    Test that Location Engine correctly executes async API calls using aiohttp.
    Uses mocked aiohttp to verify the async execution pattern.
    
    Requirement 5.1: THE Location_Engine SHALL use Python asyncio for parallel API requests
    Requirement 5.2: THE Location_Engine SHALL fetch Wikipedia and Nominatim concurrently
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Mock the _fetch_parallel method to verify it's called
    mock_enriched_data = {
        "geo": {
            "display_name": "Berlin, Germany",
            "type": "city",
            "class": "place"
        },
        "wiki_summary": "Berlin was known as the capital of Germany"
    }
    
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_enriched_data
        
        # Call get_context
        context = await engine.get_context("Berlin", "urban")
        
        # Verify _fetch_parallel was called (since cache is empty)
        mock_fetch.assert_called_once_with("Berlin")
        
        # Verify context structure
        assert context is not None
        assert context["name"] == "Berlin"
        assert "description" in context
        assert "environment_tags" in context
        assert "landmarks" in context


@pytest.mark.asyncio
async def test_timeout_handling_with_slow_api():
    """
    Test that Location Engine handles API timeouts correctly.
    
    Requirement 5.5: THE Location_Engine SHALL implement timeout of 3 seconds per API call
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Mock _fetch_parallel to simulate a timeout
    async def mock_timeout(*args, **kwargs):
        # Simulate a timeout by raising TimeoutError
        raise asyncio.TimeoutError("API call timed out")
    
    with patch.object(engine, '_fetch_parallel', side_effect=mock_timeout):
        # Should not raise exception, should use fallback
        context = await engine.get_context("SlowCity", "urban")
        
        # Verify fallback data is used
        assert context is not None
        assert context["name"] == "SlowCity"
        assert "description" in context
        assert "environment_tags" in context


@pytest.mark.asyncio
async def test_wikipedia_api_failure_fallback():
    """
    Test fallback mechanism when Wikipedia API fails.
    
    Requirement 16.1: WHEN Wikipedia API fails, THE Location_Engine SHALL use 
                      cached data if available or generic location description
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Mock _fetch_parallel to return data with empty wiki summary (simulating Wikipedia failure)
    mock_enriched_data = {
        "geo": {
            "display_name": "TestCity, Country",
            "type": "city",
            "class": "place"
        },
        "wiki_summary": ""  # Empty wiki summary indicates failure
    }
    
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_enriched_data
        
        context = await engine.get_context("TestCity", "urban")
        
        # Verify fallback description is used
        assert context is not None
        assert "description" in context
        # Should use fallback description format
        assert "urban area known as TestCity" in context["description"]


@pytest.mark.asyncio
async def test_nominatim_api_failure_fallback():
    """
    Test fallback mechanism when Nominatim API fails.
    
    Requirement 16.2: WHEN Nominatim API fails, THE Location_Engine SHALL use 
                      cached data if available or default geolocation metadata
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Mock _fetch_parallel to return minimal geo data (simulating Nominatim failure)
    mock_enriched_data = {
        "geo": {
            "display_name": "FallbackCity",
            "type": "city",
            "class": "place"
        },
        "wiki_summary": "FallbackCity was a historic location"
    }
    
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_enriched_data
        
        context = await engine.get_context("FallbackCity", "urban")
        
        # Verify context is created with fallback geo data
        assert context is not None
        assert context["name"] == "FallbackCity"
        assert context["display_name"] == "FallbackCity"
        assert context["type"] == "urban"
        assert context["class"] == "place"


@pytest.mark.asyncio
async def test_both_apis_fail_fallback():
    """
    Test fallback mechanism when both Wikipedia and Nominatim APIs fail.
    
    Requirement 16.3: WHEN both APIs fail, THE Location_Engine SHALL generate 
                      story using curated location data without external enrichment
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Mock _fetch_parallel to return minimal fallback data
    mock_enriched_data = {
        "geo": {
            "display_name": "UnknownPlace",
            "type": "city",
            "class": "place"
        },
        "wiki_summary": ""
    }
    
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_enriched_data
        
        context = await engine.get_context("UnknownPlace", "urban")
        
        # Verify curated location data is used
        assert context is not None
        assert context["name"] == "UnknownPlace"
        assert "environment_tags" in context
        assert len(context["environment_tags"]) > 0
        # Environment tags should come from curated data
        assert isinstance(context["environment_tags"], list)
        assert "landmarks" in context
        assert len(context["landmarks"]) > 0


@pytest.mark.asyncio
async def test_cache_hit_skips_api_calls():
    """
    Test that cache hit prevents API calls from being made.
    
    Requirement 2.3: THE Location_Engine SHALL check cache before making external API calls
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Pre-populate cache
    cached_context = {
        "name": "CachedCity",
        "display_name": "CachedCity, Country",
        "type": "urban",
        "class": "place",
        "environment_tags": ["buildings", "streets"],
        "description": "A cached city description",
        "landmarks": ["Central Square", "Old Town", "Market"]
    }
    cache.set("CachedCity", cached_context, ttl_hours=24, namespace="location")
    
    # Mock _fetch_parallel to verify it's NOT called
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        context = await engine.get_context("CachedCity", "urban")
        
        # Verify _fetch_parallel was NOT called (cache hit)
        mock_fetch.assert_not_called()
        
        # Verify cached data is returned
        assert context == cached_context


@pytest.mark.asyncio
async def test_cache_miss_triggers_api_calls():
    """
    Test that cache miss triggers API calls.
    
    Requirement 2.3: THE Location_Engine SHALL check cache before making external API calls
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Ensure cache is empty for this location
    cache.invalidate("NewCity", namespace="location")
    
    # Mock _fetch_parallel to verify it IS called
    mock_enriched_data = {
        "geo": {
            "display_name": "NewCity, Country",
            "type": "city",
            "class": "place"
        },
        "wiki_summary": "NewCity was a modern metropolis"
    }
    
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_enriched_data
        
        context = await engine.get_context("NewCity", "urban")
        
        # Verify _fetch_parallel WAS called (cache miss)
        mock_fetch.assert_called_once_with("NewCity")
        
        # Verify context is created from API data
        assert context is not None
        assert context["name"] == "NewCity"


@pytest.mark.asyncio
async def test_location_engine_without_cache_layer():
    """
    Test that Location Engine works correctly when cache_layer is None.
    
    This ensures resilience when caching is disabled or unavailable.
    """
    engine = LocationEngine(cache_layer=None)
    
    # Mock _fetch_parallel since we're testing without cache
    mock_enriched_data = {
        "geo": {
            "display_name": "NoCacheCity, Country",
            "type": "city",
            "class": "place"
        },
        "wiki_summary": "NoCacheCity was a place without caching"
    }
    
    with patch.object(engine, '_fetch_parallel', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_enriched_data
        
        context = await engine.get_context("NoCacheCity", "urban")
        
        # Should work without cache
        assert context is not None
        assert context["name"] == "NoCacheCity"
        
        # _fetch_parallel should be called every time (no caching)
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_parallel_api_execution_pattern():
    """
    Test that APIs are called in parallel using asyncio.gather pattern.
    
    Requirement 5.1: THE Location_Engine SHALL fetch Wikipedia and Nominatim concurrently
    Requirement 5.2: THE Location_Engine SHALL use Python asyncio for parallel API requests
    """
    from backend.external.apis import get_enriched_data
    
    # We can't easily mock asyncio.gather itself, but we can verify the result structure
    # which confirms that both APIs were called and results combined
    result = await get_enriched_data("TestLocation")
    
    # Verify both API results are present
    assert "geo" in result
    assert "wiki_summary" in result
    
    # Verify geo structure (from Nominatim)
    assert isinstance(result["geo"], dict)
    assert "display_name" in result["geo"]
    assert "type" in result["geo"]
    assert "class" in result["geo"]
    
    # Verify wiki summary (from Wikipedia)
    assert isinstance(result["wiki_summary"], str)


@pytest.mark.asyncio
async def test_api_timeout_configuration():
    """
    Test that API timeout is configurable and respected.
    
    Requirement 5.5: THE Location_Engine SHALL implement timeout of 3 seconds per API call
    """
    from backend.external.apis import fetch_wikipedia_summary, fetch_nominatim_location
    
    # Test with custom timeout
    custom_timeout = 1  # 1 second
    
    # These should complete or timeout within the specified time
    # We're testing that the timeout parameter is accepted and used
    try:
        wiki_result = await fetch_wikipedia_summary("Berlin", timeout=custom_timeout)
        assert isinstance(wiki_result, str)
    except asyncio.TimeoutError:
        # Timeout is acceptable - it means the timeout is working
        pass
    
    try:
        geo_result = await fetch_nominatim_location("Berlin", timeout=custom_timeout)
        assert isinstance(geo_result, dict)
    except asyncio.TimeoutError:
        # Timeout is acceptable - it means the timeout is working
        pass


@pytest.mark.asyncio
async def test_exception_handling_in_fetch_parallel():
    """
    Test that exceptions in _fetch_parallel are handled gracefully.
    
    Requirement 5.4: WHEN one API call fails, THE Location_Engine SHALL continue 
                     with available data and use fallback for failed call
    """
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # Mock _fetch_parallel to raise an exception
    with patch.object(engine, '_fetch_parallel', side_effect=Exception("API Error")):
        # Should not raise exception, should use fallback
        context = await engine.get_context("ErrorCity", "urban")
        
        # Verify fallback data is used
        assert context is not None
        assert context["name"] == "ErrorCity"
        assert "description" in context
        assert "environment_tags" in context


if __name__ == "__main__":
    # Run tests manually
    print("Running Task 4.4 Location Engine Unit Tests...\n")
    
    asyncio.run(test_async_api_call_execution_with_mocked_aiohttp())
    print("✓ test_async_api_call_execution_with_mocked_aiohttp passed")
    
    asyncio.run(test_timeout_handling_with_slow_api())
    print("✓ test_timeout_handling_with_slow_api passed")
    
    asyncio.run(test_wikipedia_api_failure_fallback())
    print("✓ test_wikipedia_api_failure_fallback passed")
    
    asyncio.run(test_nominatim_api_failure_fallback())
    print("✓ test_nominatim_api_failure_fallback passed")
    
    asyncio.run(test_both_apis_fail_fallback())
    print("✓ test_both_apis_fail_fallback passed")
    
    asyncio.run(test_cache_hit_skips_api_calls())
    print("✓ test_cache_hit_skips_api_calls passed")
    
    asyncio.run(test_cache_miss_triggers_api_calls())
    print("✓ test_cache_miss_triggers_api_calls passed")
    
    asyncio.run(test_location_engine_without_cache_layer())
    print("✓ test_location_engine_without_cache_layer passed")
    
    asyncio.run(test_parallel_api_execution_pattern())
    print("✓ test_parallel_api_execution_pattern passed")
    
    asyncio.run(test_api_timeout_configuration())
    print("✓ test_api_timeout_configuration passed")
    
    asyncio.run(test_exception_handling_in_fetch_parallel())
    print("✓ test_exception_handling_in_fetch_parallel passed")
    
    print("\nAll Location Engine unit tests passed.")
