"""
Test to verify that combining results after asyncio.gather takes < 10ms
"""
import asyncio
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest

from backend.external.apis import get_enriched_data, fetch_nominatim_location, fetch_wikipedia_summary


@pytest.mark.asyncio
async def test_combine_results_timing():
    """
    Test that combining results after both APIs return takes < 10ms.
    
    This test measures the time to combine results after asyncio.gather completes.
    Requirements: 5.3
    """
    location = "Tokyo"
    
    # First, fetch the data (this includes network time)
    geo_data, raw_wiki = await asyncio.gather(
        fetch_nominatim_location(location),
        fetch_wikipedia_summary(location),
        return_exceptions=True
    )
    
    # Now measure just the combining/processing time
    start = time.perf_counter()
    
    # Handle exceptions from gather (same logic as in get_enriched_data)
    if isinstance(geo_data, Exception):
        geo_data = {
            "display_name": location,
            "type": "city",
            "class": "place"
        }
    
    if isinstance(raw_wiki, Exception):
        raw_wiki = ""
    
    # Create the result dictionary (combining step)
    from backend.external.apis import narrativize_wiki
    result = {
        "geo": geo_data,
        "wiki_summary": narrativize_wiki(location, raw_wiki) if raw_wiki else ""
    }
    
    combine_time = time.perf_counter() - start
    combine_time_ms = combine_time * 1000
    
    print(f"Combining time: {combine_time_ms:.3f}ms")
    
    # Verify combining takes < 10ms
    assert combine_time_ms < 10.0, f"Combining took {combine_time_ms:.3f}ms, should be < 10ms"
    
    # Verify result structure
    assert "geo" in result
    assert "wiki_summary" in result


@pytest.mark.asyncio
async def test_get_enriched_data_includes_combining():
    """
    Test that get_enriched_data properly combines results.
    
    This verifies the complete implementation meets requirements.
    Requirements: 5.1, 5.3, 5.4
    """
    location = "Berlin"
    
    result = await get_enriched_data(location)
    
    # Verify structure
    assert isinstance(result, dict)
    assert "geo" in result
    assert "wiki_summary" in result
    
    # Verify geo data structure
    assert isinstance(result["geo"], dict)
    assert "display_name" in result["geo"]
    assert "type" in result["geo"]
    assert "class" in result["geo"]
    
    # Verify wiki summary is a string
    assert isinstance(result["wiki_summary"], str)
    
    print(f"✓ get_enriched_data returns properly combined results")


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_combine_results_timing())
    print("✓ test_combine_results_timing passed")
    
    asyncio.run(test_get_enriched_data_includes_combining())
    print("✓ test_get_enriched_data_includes_combining passed")
    
    print("\nAll combining timing tests passed!")
