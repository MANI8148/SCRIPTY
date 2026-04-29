"""
SCRIPTY - Location Engine (V3 - Enriched)
Uses external APIs for real-world data and provides fallback curated context.
"""
import random
try:
    from backend.external.apis import get_enriched_data
    from backend.data.curated_lists import CURATED_LOCATIONS
except ImportError:
    from external.apis import get_enriched_data
    from data.curated_lists import CURATED_LOCATIONS

class LocationEngine:
    def __init__(self):
        self.curated_locations = CURATED_LOCATIONS

    def get_context(self, location_name: str, location_type: str = "urban"):
        """
        Enriches a location with real-world data and falls back to curated lists.
        """
        # Fetch external data (wiki + Nominatim)
        enriched = get_enriched_data(location_name)
        geo = enriched["geo"]
        wiki = enriched["wiki_summary"]
        
        # Determine environment based on location type and API data
        env = self.curated_locations.get(location_type, self.curated_locations["urban"])
        
        # Add API info if available
        desc = wiki if wiki else f"A {location_type} area known as {location_name}."
        
        context = {
            "name": location_name,
            "display_name": geo.get("display_name", location_name),
            "type": location_type,
            "class": geo.get("class", "place"),
            "environment_tags": env,
            "description": desc,
            "landmarks": [geo.get("display_name", location_name).split(",")[0]] + [random.choice(env) for _ in range(2)]
        }
        
        return context

if __name__ == "__main__":
    engine = LocationEngine()
    print(engine.get_context("Hyderabad", "metro"))
