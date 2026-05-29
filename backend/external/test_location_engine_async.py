"""
Test for async Location Engine implementation
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from backend.external.location_engine import LocationEngine
from backend.cache.cache_layer import CacheLayer


@pytest.mark.asyncio
async def test_location_engine_async_basic():
    """Test that LocationEngine.get_context works with async/await"""
    engine = LocationEngine()
    
    # Test basic async call
    context = await engine.get_context("London", "urban")
    
    assert context is not None
    assert "name" in context
    assert context["name"] == "London"
    assert "description" in context
    assert "environment_tags" in context
    assert "landmarks" in context


@pytest.mark.asyncio
async def test_location_engine_with_cache():
    """Test that LocationEngine uses cache correctly"""
    cache = CacheLayer(fallback_to_memory=True)
    engine = LocationEngine(cache_layer=cache)
    
    # First call - should be cache miss
    context1 = await engine.get_context("Paris", "urban")
    stats1 = cache.get_stats()
    
    # Second call - should be cache hit
    context2 = await engine.get_context("Paris", "urban")
    stats2 = cache.get_stats()
    
    # Verify both contexts are identical
    assert context1 == context2
    
    # Verify cache hit rate increased
    assert stats2["hits"] > stats1["hits"]


@pytest.mark.asyncio
async def test_location_engine_parallel_calls():
    """Test that multiple location requests can be made in parallel"""
    engine = LocationEngine()
    
    # Make multiple parallel requests
    results = await asyncio.gather(
        engine.get_context("Tokyo", "metro"),
        engine.get_context("New York", "metro"),
        engine.get_context("Mumbai", "metro")
    )
    
    assert len(results) == 3
    assert all(r is not None for r in results)
    assert results[0]["name"] == "Tokyo"
    assert results[1]["name"] == "New York"
    assert results[2]["name"] == "Mumbai"


@pytest.mark.asyncio
async def test_location_engine_fallback():
    """Test that LocationEngine falls back gracefully when APIs fail"""
    engine = LocationEngine()
    
    # Use a nonsense location that will likely fail API calls
    context = await engine.get_context("XYZ_NONEXISTENT_PLACE_12345", "urban")
    
    # Should still return a valid context with fallback data
    assert context is not None
    assert "name" in context
    assert "description" in context
    assert "environment_tags" in context


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_location_engine_async_basic())
    print("✓ test_location_engine_async_basic passed")
    
    asyncio.run(test_location_engine_with_cache())
    print("✓ test_location_engine_with_cache passed")
    
    asyncio.run(test_location_engine_parallel_calls())
    print("✓ test_location_engine_parallel_calls passed")
    
    asyncio.run(test_location_engine_fallback())
    print("✓ test_location_engine_fallback passed")
    
    print("\nAll tests passed!")
