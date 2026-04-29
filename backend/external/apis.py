import requests
import time
import random

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

def fetch_wikipedia_summary(title: str) -> str:
    """
    Fetches the first-paragraph summary of a topic from Wikipedia.
    Returns empty string if failed.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        formatted_title = title.replace(" ", "_").capitalize()
        resp = requests.get(f"{WIKIPEDIA_API_URL}{formatted_title}", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("extract", "")
    except Exception:
        pass
    
    return ""

def fetch_nominatim_location(location_name: str) -> dict:
    """
    Fetches real geographical metadata for a location from OpenStreetMap.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        params = {
            "q": location_name,
            "format": "json",
            "limit": 1
        }
        resp = requests.get(NOMINATIM_API_URL, params=params, headers=headers, timeout=5)
        
        time.sleep(1) # Be nice to nominatim API
        
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 0:
                item = data[0]
                return {
                    "display_name": item.get("display_name", location_name),
                    "type": item.get("type", "region"),
                    "class": item.get("class", "place")
                }
    except Exception:
        pass
        
    return {
        "display_name": location_name,
        "type": "city",
        "class": "place"
    }

def get_enriched_data(location: str) -> dict:
    """Returns combined Wikipedia and OSM data with narrativized summary."""
    geo_data = fetch_nominatim_location(location)
    raw_wiki = fetch_wikipedia_summary(location)
    
    return {
        "geo": geo_data,
        "narrative_desc": narrativize_wiki(location, raw_wiki)
    }
import re # Added import for regex in narrativize_wiki
