"""
SCRIPTY - India Timeline Utility (V3 - Dynamic)
Provides temporal context based on mathematical year ranges.
"""

class IndiaTimeline:
    ERAS = [
        {"name": "ancient", "range": range(-10000, 1200), "description": "Ancient civilization and empire building."},
        {"name": "pre_colonial", "range": range(1200, 1757), "description": "Medieval sultanates and the Mughal Empire."},
        {"name": "colonial", "range": range(1757, 1947), "description": "British East India Company and Raj rule."},
        {"name": "modern", "range": range(1947, 2010), "description": "Post-independence development and global integration."},
        {"name": "digital", "range": range(2010, 2100), "description": "Information age and rapid technology advancement."},
        {"name": "future", "range": range(2100, 3001), "description": "Speculative future shaped by advanced systems and new social orders."}
    ]

    @classmethod
    def get_era(cls, year: int) -> dict:
        """Determines the era based on the provided year."""
        for era in cls.ERAS:
            if year in era["range"]:
                return era
        return {"name": "mythic", "description": "A custom or mythic period outside standard chronology."}

    @classmethod
    def get_temporal_context(cls, year: int) -> dict:
        """Returns enriched temporal metadata for a given year."""
        era = cls.get_era(year)
        
        # Dynamic context based on era
        if era["name"] == "ancient":
            return {
                "era": era["name"],
                "tech": "manual",
                "tone": "epic, spiritual",
                "infrastructure": ["stone temples", "earthwork forts", "river trade"],
                "transport": ["chariots", "elephants", "walking"]
            }
        elif era["name"] == "pre_colonial":
            return {
                "era": era["name"],
                "tech": "mechanical-early",
                "tone": "ornate, imperial",
                "infrastructure": ["marble palaces", "walled cities", "grand gardens"],
                "transport": ["horse carriages", "royal palanquins", "boats"]
            }
        elif era["name"] == "colonial":
            return {
                "era": era["name"],
                "tech": "industrial",
                "tone": "tense, changing",
                "infrastructure": ["telegraph offices", "railway tracks", "colonial bungalows"],
                "transport": ["steam trains", "trams", "automobiles"]
            }
        elif era["name"] == "modern":
            return {
                "era": era["name"],
                "tech": "electronic",
                "tone": "fast-paced, hopeful",
                "infrastructure": ["planned sectors", "factories", "public universities"],
                "transport": ["buses", "cycles", "early cars"]
            }
        elif era["name"] == "digital":
            return {
                "era": era["name"],
                "tech": "digital",
                "tone": "vibrant, connected",
                "infrastructure": ["smart cities", "it hubs", "glass skyscrapers"],
                "transport": ["metro trains", "ride-sharing", "electric vehicles"]
            }
        elif era["name"] == "future":
            return {
                "era": era["name"],
                "tech": "advanced",
                "tone": "speculative, unstable",
                "infrastructure": ["orbital links", "adaptive districts", "autonomous transit"],
                "transport": ["maglev corridors", "electric airships", "self-driving fleets"]
            }
        return {
            "era": era["name"],
            "tech": "custom",
            "tone": "mythic, flexible",
            "infrastructure": ["legendary roads", "improvised settlements", "symbolic landmarks"],
            "transport": ["walking", "caravans", "unusual conveyances"]
        }

if __name__ == "__main__":
    print(IndiaTimeline.get_temporal_context(1920))
