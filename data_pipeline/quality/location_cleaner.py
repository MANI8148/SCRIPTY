"""
Location Cleaner Module

Filters out generic/invalid location values from NarrativeFragment location fields.
Classifies locations as valid/invalid based on known location lists and heuristics.
Extracts proper location names from text using pattern matching.
"""

from typing import List, Dict, Set, Optional, Tuple
import re
import logging
from collections import Counter

from data_pipeline.schema.fragment import NarrativeFragment


logger = logging.getLogger(__name__)


# Generic/single-word location words that should not be used as location names
# when standing alone (they may be valid as part of a multi-word location)
GENERIC_LOCATIONS: Set[str] = {
    # Abstract time periods (NOT locations)
    "age", "era", "epoch", "period", "reign", "century", "decade", "millennium",
    "year", "month", "week", "day", "time", "season", "summer", "winter",

    # Generic place words (too vague to be useful)
    "place", "spot", "area", "region", "zone", "section", "part", "side",
    "end", "edge", "corner", "center", "middle", "heart",

    # Generic buildings/structures (valid as specific named locations but not
    # standalone)
    "house", "home", "room", "hall", "chamber", "building", "structure",
    "tower", "castle", "palace", "fort", "fortress", "citadel", "temple",
    "church", "cathedral", "shrine", "monastery", "abbey", "school",
    "college", "university", "hospital", "prison", "jail", "dungeon",
    "gate", "door", "wall", "bridge", "road", "street", "lane", "path",
    "way", "route", "trail", "alley", "square", "court", "yard",
    "garden", "park", "market", "shop", "store", "inn", "tavern",
    "hotel", "bank", "office", "studio", "theatre", "theater",
    "museum", "library", "archive", "gallery", "stadium", "arena",

    # Natural features (too generic standalone)
    "mountain", "hill", "valley", "plain", "desert", "forest", "woods",
    "jungle", "swamp", "marsh", "lake", "river", "stream", "creek",
    "pond", "sea", "ocean", "bay", "gulf", "cove", "beach", "shore",
    "coast", "island", "peninsula", "cape", "cliff", "cave", "cavern",
    "field", "meadow", "farm", "land", "ground", "earth",

    # Settlement types (too generic standalone)
    "city", "town", "village", "hamlet", "settlement", "outpost",
    "camp", "port", "harbor", "capital", "metropolis", "borough",
    "district", "quarter", "neighborhood", "suburb", "province",
    "state", "county", "parish", "kingdom", "empire", "republic",
    "nation", "country", "land", "territory", "colony",

    # Generic landscape features
    "sky", "horizon", "view", "scenery", "landscape", "panorama",
    "tree", "flower", "plant", "grove", "orchard", "vineyard",
    "garden", "park", "lawn", "courtyard", "terrace", "balcony",
    "entrance", "exit", "passage", "corridor", "hallway", "staircase",
    "roof", "attic", "basement", "cellar", "floor", "ceiling",

    # Rooms and interior spaces
    "kitchen", "bedroom", "bathroom", "living room", "dining room",
    "study", "library", "office", "den", "cellar", "attic",
    "basement", "hallway", "corridor", "entrance", "foyer",
    "lobby", "parlor", "sitting room", "drawing room", "ballroom",
    "dining hall", "great hall", "throne room", "war room",
    "waiting room", "meeting room", "conference room", "classroom",

    # Misc
    "machine", "vehicle", "carriage", "train", "ship", "boat",
    "station", "stop", "platform", "dock", "pier", "wharf",
    "farm", "ranch", "plantation", "estate", "manor",
    "window", "doorway", "archway", "gateway", "threshold",
}


# Multi-word patterns that signal valid specific locations
SPECIFIC_LOCATION_PATTERNS = [
    re.compile(r'\b(?:the\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b'),  # "New York", "San Francisco"
    re.compile(r'\b(?:the\s+)?[A-Z][a-z]+\s+(?:Street|Road|Avenue|Lane|Drive|Way|Place|Square|Court|Park|Gardens|Terrace|Close|Hill|View|House|Hall|Castle|Tower|Bridge|Gate|Church|Abbey|School|College|Hospital|Hotel|Inn|Tavern|Museum|Theatre|Library|Station|Harbour|Harbor|Port|Fort|Mount|Lake|River|Sea|Bay|Cape|Island|Valley|Forest|Woods|Field|Farm|Manor|Estate|Palace|Temple|Shrine|Monastery)\b'),  # "Baker Street", "Victoria Station"
    re.compile(r'\b(?:the\s+)?(?:Lake|Mount|Mountains|River|Sea|Cape|Fort|Port|New|Old|North|South|East|West)\s+[A-Z][a-z]+\b'),  # "Lake Geneva", "New York"
    re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Palace|Castle|Tower|Bridge|Gate|Square|Gardens|Museum|Theatre|Abbey)\b'),
]


# Known valid specific locations (cities, countries, regions, etc.)
KNOWN_LOCATIONS: Set[str] = {
    # Major world cities
    "london", "paris", "rome", "berlin", "moscow", "madrid", "vienna",
    "warsaw", "prague", "budapest", "athens", "istanbul", "cairo",
    "jerusalem", "damascus", "baghdad", "tehran", "kabul", "delhi",
    "mumbai", "bombay", "calcutta", "kolkata", "madras", "chennai",
    "hyderabad", "bangalore", "bengaluru", "pune", "ahmedabad",
    "beijing", "shanghai", "hong kong", "tokyo", "kyoto", "osaka",
    "seoul", "bangkok", "singapore", "kuala lumpur", "jakarta",
    "manila", "sydney", "melbourne", "auckland", "wellington",
    "new york", "los angeles", "chicago", "san francisco",
    "boston", "washington", "philadelphia", "miami", "toronto",
    "montreal", "vancouver", "mexico city", "buenos aires",
    "rio de janeiro", "sao paulo", "santiago", "lima", "bogota",

    # Countries
    "england", "france", "germany", "italy", "spain", "portugal",
    "russia", "china", "india", "japan", "korea", "vietnam",
    "thailand", "burma", "myanmar", "indonesia", "philippines",
    "australia", "new zealand", "canada", "america", "united states",
    "brazil", "argentina", "chile", "peru", "colombia", "venezuela",
    "egypt", "morocco", "algeria", "tunisia", "libya", "sudan",
    "ethiopia", "kenya", "tanzania", "nigeria", "ghana", "south africa",
    "turkey", "iran", "iraq", "afghanistan", "pakistan", "nepal",
    "switzerland", "sweden", "norway", "finland", "denmark",
    "netherlands", "belgium", "austria", "poland", "czech republic",
    "greece", "hungary", "romania", "bulgaria", "yugoslavia",

    # Regions/continents
    "europe", "asia", "africa", "north america", "south america",
    "australia", "antarctica", "middle east", "far east",
    "indies", "west indies", "east indies",
    "britannia", "gaul", "iberia", "scandinavia", "siberia",
    "bengal", "punjab", "rajasthan", "kashmir", "gujarat",
    "normandy", "brittany", "provence", "bavaria", "prussia",
    "sicily", "sardinia", "corsica", "crete", "cyprus",
    "arabia", "persia", "mesopotamia", "anatolia",
    "nubia", "abyssinia", "carthage", "numidia",

    # Seas, oceans, rivers, mountains
    "atlantic", "pacific", "indian ocean", "mediterranean",
    "english channel", "red sea", "black sea", "caspian sea",
    "baltic sea", "north sea", "adriatic sea", "aegean sea",
    "alps", "himalayas", "andes", "rockies", "urals",
    "nile", "amazon", "mississippi", "ganges", "yangtze",
    "danube", "rhine", "thames", "seine", "loire",
    "volga", "don", "dnieper", "indus", "brahmaputra",

    # Famous streets/districts
    "wall street", "broadway", "fifth avenue", "champs-elysees",
    "downing street", "baker street", "oxford street", "regent street",
    "saville row", "whitehall", "strand", "fleet street",
    "piccadilly", "times square", "trafalgar square",
    "red square", "tiananmen square",

    # Historical locations
    "babylon", "persepolis", "pompeii", "sodom", "gomorrah",
    "camelot", "avalon", "atlantis", "el dorado",
    "troy", "mycenae", "knossos", "carthage", "granite house",
    "constantinople", "byzantium",
    "suez", "panama", "gibraltar",
}


class LocationCleaner:
    """Cleans location fields in NarrativeFragments by filtering out
    generic/invalid location entries."""

    def __init__(self):
        self.generic_locations = {w.lower() for w in GENERIC_LOCATIONS}
        self.known_locations = {w.lower() for w in KNOWN_LOCATIONS}
        self.specific_patterns = SPECIFIC_LOCATION_PATTERNS
        # Additional words that look like locations but are actually character names/roles
        self.character_words: Set[str] = {
            "don", "dona", "donna", "monsieur", "madame", "mademoiselle",
            "monte cristo", "cyrus harding", "jean valjean", "hester prynne",
            "porthos", "athos", "aramis", "d'artagnan",
        }
        self.stats = {
            "total_locations_checked": 0,
            "invalid_locations": 0,
            "fragments_cleaned": 0,
            "fragments_seen": 0,
            "invalid_by_type": Counter(),
            "most_common_invalid": Counter(),
        }

    def _is_valid_location(self, location: str, text: str = "",
                           participants: List[str] = None) -> Tuple[bool, str]:
        """Check if a location value is valid.
        Returns (is_valid, reason)."""
        loc = location.strip()
        loc_lower = loc.lower()
        participants = participants or []

        if not loc:
            return False, "empty"

        self.stats["total_locations_checked"] += 1

        # Reject if it's a known character word
        if loc_lower in self.character_words:
            self.stats["invalid_by_type"]["character_word"] += 1
            self.stats["most_common_invalid"][loc_lower] += 1
            return False, "character_word"

        # Reject if it matches a participant (it's a character name, not a location)
        for p in participants:
            if p.strip().lower() == loc_lower:
                self.stats["invalid_by_type"]["matches_participant"] += 1
                return False, "matches_participant"

        # Check known locations first
        if loc_lower in self.known_locations:
            return True, "known_location"

        # Check if it matches a specific location pattern (multi-word proper name)
        if self._matches_specific_pattern(loc):
            return True, "specific_pattern"

        # Check if it's a generic/forbidden location
        if loc_lower in self.generic_locations:
            self.stats["invalid_by_type"]["generic_word"] += 1
            self.stats["most_common_invalid"][loc_lower] += 1
            return False, "generic_word"

        # Check if it looks like a proper location name (multi-word, capitalized)
        words = loc.split()
        if len(words) >= 2:
            # Multi-word with all words capitalized
            if all(w[0].isupper() if w else False for w in words if w[0].isalpha()):
                return True, "multi_word_proper"

        # Single-word location that is capitalized and not generic
        if len(words) == 1:
            word = words[0]
            # Must start with capital letter
            if not word[0].isupper():
                self.stats["invalid_by_type"]["not_capitalized"] += 1
                self.stats["most_common_invalid"][loc_lower] += 1
                return False, "not_capitalized"

            # Allow common character names that are also locations
            # (like "Paris" which is a person's name too)
            if loc_lower in {"paris", "alexandria", "victoria", "alexander",
                             "florence", "adelaide", "georgia", "virginia",
                             "carolina", "brittany"}:
                # Check if location-specific context exists
                if text and self._has_location_context(text):
                    return True, "proper_name_with_context"
                # Without context, keep as location since it's a known city/region
                return True, "known_ambiguous"

            # Location-like words
            if self._is_location_like(word):
                return True, "location_like_word"

        # For anything else, check if it's a proper noun in text with location context
        if text and loc_lower not in self.generic_locations:
            if self._has_location_context(text) and self._is_proper_noun_in_text(loc, text):
                return True, "proper_noun_in_text"

        self.stats["invalid_by_type"]["unknown"] += 1
        self.stats["most_common_invalid"][loc_lower] += 1
        return False, "unknown"

    def _matches_specific_pattern(self, location: str) -> bool:
        """Check if location matches a valid specific location pattern."""
        for pattern in self.specific_patterns:
            if pattern.fullmatch(location.strip()):
                return True
        return False

    def _is_location_like(self, word: str) -> bool:
        """Check if a word looks like a location name."""
        # Ends with common location suffixes
        location_suffixes = [
            "burg", "burgh", "bury", "ford", "ham", "shire", "stead",
            "town", "wick", "worth", "ville", "mont", "port", "grad",
            "polis", "bad", "berg", "dorf", "feld", "furt", "hausen",
            "heim", "land", "stein", "thal", "wald", "wich",
        ]
        word_lower = word.lower()
        for suffix in location_suffixes:
            if word_lower.endswith(suffix) and len(word) > len(suffix) + 2:
                return True

        # Common location prefixes
        location_prefixes = [
            "san", "santa", "santo", "saint", "st", "mount", "fort",
            "new", "old", "north", "south", "east", "west", "port",
            "upper", "lower", "great", "little",
        ]
        for prefix in location_prefixes:
            if word_lower.startswith(prefix) and len(word_lower) > len(prefix) + 1:
                return True

        return False

    def _has_location_context(self, text: str) -> bool:
        """Check if text has words that suggest a location context."""
        text_lower = text.lower()
        location_context_words = [
            "in", "at", "to", "from", "through", "toward", "into",
            "arrived", "left", "traveled", "journey", "visited",
            "reached", "entered", "departed", "came", "went",
            "city", "town", "village", "street", "road", "square",
        ]
        return any(w in text_lower for w in location_context_words)

    def _is_proper_noun_in_text(self, location: str, text: str) -> bool:
        """Check if the location appears as a proper noun in the text."""
        escaped = re.escape(location)
        # Look for the word as a proper noun (capitalized)
        pattern = re.compile(r'\b' + escaped + r'\b')
        return bool(pattern.search(text))

    def clean_fragment(self, frag: NarrativeFragment) -> Optional[str]:
        """Clean a single fragment's location field.
        Returns the cleaned location value or None if invalid."""
        self.stats["fragments_seen"] += 1

        if not frag.location:
            return None

        is_valid, reason = self._is_valid_location(
            frag.location, frag.text, frag.participants
        )

        if not is_valid:
            self.stats["invalid_locations"] += 1
            self.stats["fragments_cleaned"] += 1
            # Try to extract a better location from text
            extracted = self._extract_location_from_text(frag.text)
            if extracted:
                frag.location = extracted
                self.stats["invalid_by_type"]["replaced_with_extraction"] += 1
                return extracted

            frag.location = ""
            return None

        return frag.location

    def _extract_location_from_text(self, text: str) -> Optional[str]:
        """Try to extract a valid location name from text."""
        text_lower = text.lower()

        # First check for known locations in text (with word boundaries)
        for loc in sorted(self.known_locations, key=len, reverse=True):
            # Use word boundaries + avoid matching contractions (e.g., "don" in "don't")
            # The negative lookahead (?!['\u2019]\w) prevents matching before apostrophe+letter
            loc_pattern = re.compile(
                r'\b' + re.escape(loc) + r'\b(?![\'\u2019]\w)',
                re.IGNORECASE
            )
            match = loc_pattern.search(text)
            if match:
                extracted = match.group().strip()
                # Verify this is not a substring of a larger word
                # (e.g., "don" should not match "donation" even with \b)
                if extracted.lower() == loc:
                    return extracted

        # Check for multi-word capitalized location patterns
        for pattern in self.specific_patterns:
            matches = pattern.findall(text)
            for match in matches:
                match_clean = match.strip()
                match_lower = match_clean.lower()
                if (match_lower not in self.generic_locations
                        and match_lower not in self.character_words):
                    return match_clean

        # Check for single-word capitalized locations that look like place names
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        for w in words:
            w_lower = w.lower()
            # Skip character words and known non-locations
            if w_lower in self.character_words:
                continue
            # Skip honorifics and titles
            if w_lower in {"don", "dona", "sir", "lord", "lady", "mr", "mrs",
                            "miss", "madam", "dr", "prof", "captain", "colonel",
                            "major", "general", "king", "queen", "prince",
                            "princess", "duke", "duchess", "count", "countess",
                            "monsieur", "madame", "mademoiselle", "saint",
                            "santo", "santa", "father", "mother", "brother"}:
                continue
            # Skip common English words that are not locations
            if w_lower in {"still", "yet", "thus", "hence", "thence", "whence",
                            "here", "there", "where", "while", "whilst",
                            "indeed", "however", "therefore", "nevertheless",
                            "nonetheless", "furthermore", "moreover",
                            "meanwhile", "afterwards", "beforehand",
                            "besides", "likewise", "else", "otherwise"}:
                continue
            if w_lower in self.known_locations:
                return w
            if self._is_location_like(w) and w_lower not in self.generic_locations:
                return w

        return None

    def clean_fragments(
        self, fragments: List[NarrativeFragment]
    ) -> List[NarrativeFragment]:
        """Clean all fragments' location fields."""
        for frag in fragments:
            self.clean_fragment(frag)

        if self.stats["total_locations_checked"] > 0:
            invalid_rate = round(
                self.stats["invalid_locations"]
                / self.stats["total_locations_checked"]
                * 100,
                2,
            )
        else:
            invalid_rate = 0.0

        logger.info(
            f"Location cleanup: {self.stats['fragments_seen']} fragments, "
            f"{self.stats['total_locations_checked']} locations checked, "
            f"{self.stats['invalid_locations']} invalid ({invalid_rate}%), "
            f"{self.stats['fragments_cleaned']} fragments affected"
        )

        return fragments

    def get_stats(self) -> Dict:
        """Get cleanup statistics."""
        stats = dict(self.stats)
        stats["invalid_by_type"] = dict(self.stats["invalid_by_type"])
        stats["most_common_invalid"] = dict(
            self.stats["most_common_invalid"].most_common(20)
        )
        if self.stats["total_locations_checked"] > 0:
            stats["invalid_rate"] = round(
                self.stats["invalid_locations"]
                / self.stats["total_locations_checked"]
                * 100,
                2,
            )
        else:
            stats["invalid_rate"] = 0.0
        return stats
