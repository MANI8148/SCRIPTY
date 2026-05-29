import asyncio
import random
import re
from typing import Optional

import aiohttp

try:
    from backend.config import Config
except ImportError:
    from config import Config

WIKIPEDIA_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "M26StoryEngine/1.0"

def narrativize_wiki(title: str, extract: str) -> str:
    """
    Summarizes the first sentence of a Wikipedia extract and reformats it 
    into a natural storytelling description.
    """
    if not extract:
        return f"{title} was a place of deep intrigue and ancient roots."
    
    # Extract the first sentence
    first_sentence = extract.split(". ")[0].strip()
    
    # Remove technical jargon from the start (e.g., "(born 1900)", "in the state of")
    clean_fact = re.sub(r'\(.*?\)', '', first_sentence)
    clean_fact = clean_fact.replace(" is a", " was known as a").replace(" is the", " stood as the")
    clean_fact = clean_fact.replace(" is ", " was ").replace(" are ", " were ")
    
    # Capitalize proper nouns within the fact if they were lowercase
    def cap_proper(match):
        word = match.group(0)
        return word.capitalize()
    
    # Very basic list of words to capitalize if found in lower case (e.g., 'india', 'telangana')
    important_regions = ["india", "telangana", "hyderabad", "deccan", "bengal"]
    for region in important_regions:
        clean_fact = re.sub(rf'\b{region}\b', region.capitalize(), clean_fact, flags=re.IGNORECASE)

    templates = [
        f"which {clean_fact.lower().replace(title.lower(), '').strip(', ')}",
        f"a site that {clean_fact.lower().replace(title.lower(), '').strip(', ')}",
        f"recognized as {clean_fact.lower().replace(title.lower(), '').strip(', ')}"
    ]
    
    narrative = random.choice(templates)
    return narrative.strip(". ")

async def fetch_wikipedia_summary(title: str, timeout: Optional[int] = None) -> str:
    """
    Fetches the first-paragraph summary of a topic from Wikipedia asynchronously.
    Returns empty string if failed.
    
    Args:
        title: Wikipedia article title
        timeout: Timeout in seconds (defaults to Config.API_TIMEOUT_SECONDS)
    
    Returns:
        Wikipedia extract text or empty string on failure
    """
    if timeout is None:
        timeout = Config.API_TIMEOUT_SECONDS
    
    try:
        headers = {"User-Agent": USER_AGENT}
        formatted_title = title.replace(" ", "_").capitalize()
        url = f"{WIKIPEDIA_API_URL}{formatted_title}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                headers=headers, 
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("extract", "")
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass
    
    return ""

async def fetch_nominatim_location(location_name: str, timeout: Optional[int] = None) -> dict:
    """
    Fetches real geographical metadata for a location from OpenStreetMap asynchronously.
    
    Args:
        location_name: Name of the location to search for
        timeout: Timeout in seconds (defaults to Config.API_TIMEOUT_SECONDS)
    
    Returns:
        Dictionary with display_name, type, and class fields
    """
    if timeout is None:
        timeout = Config.API_TIMEOUT_SECONDS
    
    try:
        headers = {"User-Agent": USER_AGENT}
        params = {
            "q": location_name,
            "format": "json",
            "limit": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                NOMINATIM_API_URL, 
                params=params, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) > 0:
                        item = data[0]
                        return {
                            "display_name": item.get("display_name", location_name),
                            "type": item.get("type", "region"),
                            "class": item.get("class", "place")
                        }
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass
        
    return {
        "display_name": location_name,
        "type": "city",
        "class": "place"
    }

async def get_enriched_data(location: str, timeout: Optional[int] = None) -> dict:
    """
    Returns combined Wikipedia and OSM data with narrativized summary.
    Fetches both APIs in parallel using asyncio.gather for improved performance.
    
    Args:
        location: Location name to enrich
        timeout: Timeout in seconds per API call (defaults to Config.API_TIMEOUT_SECONDS)
    
    Returns:
        Dictionary with 'geo' and 'wiki_summary' keys
    """
    # Fetch both APIs in parallel
    geo_data, raw_wiki = await asyncio.gather(
        fetch_nominatim_location(location, timeout),
        fetch_wikipedia_summary(location, timeout),
        return_exceptions=True
    )
    
    # Handle exceptions from gather
    if isinstance(geo_data, Exception):
        geo_data = {
            "display_name": location,
            "type": "city",
            "class": "place"
        }
    
    if isinstance(raw_wiki, Exception):
        raw_wiki = ""
    
    return {
        "geo": geo_data,
        "wiki_summary": narrativize_wiki(location, raw_wiki) if raw_wiki else ""
    }
