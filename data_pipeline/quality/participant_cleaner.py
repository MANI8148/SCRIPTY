"""
Participant Cleaner Module

Filters out non-character participants (locations, months, common nouns,
prepositions, verbs, adjectives) from NarrativeFragment participant lists.

Uses NER-like pattern matching combined with stop-word lists and
cross-references with known character names extracted from source books.
"""

from typing import List, Dict, Set, Optional
import re
import logging
from collections import Counter, defaultdict

from data_pipeline.schema.fragment import NarrativeFragment


logger = logging.getLogger(__name__)


# Words that should NEVER be considered character names
STOP_WORDS: Set[str] = {
    # Common determiners and pronouns
    "the", "a", "an", "this", "that", "these", "those", "it", "its",
    "he", "she", "they", "them", "we", "us", "our", "my", "your", "his", "her",
    "their", "itself", "himself", "herself", "themselves", "myself", "yourself",
    "i", "me", "mine", "yours", "his", "hers", "theirs", "ours",
    "who", "whom", "whose", "which", "what",

    # Prepositions
    "about", "above", "across", "after", "against", "along", "among", "around",
    "at", "before", "behind", "below", "beneath", "beside", "between", "beyond",
    "by", "down", "during", "except", "for", "from", "in", "inside", "into",
    "near", "of", "off", "on", "out", "outside", "over", "through", "throughout",
    "to", "toward", "under", "until", "up", "upon", "with", "within", "without",

    # Conjunctions
    "and", "but", "or", "nor", "yet", "so", "for", "because", "although",
    "while", "if", "since", "unless", "until", "after", "before", "when",

    # Common verbs (past/participle that look like names when capitalized)
    "said", "was", "were", "had", "been", "being", "having", "doing", "made",
    "took", "taken", "given", "gave", "went", "gone", "come", "came", "seen",
    "saw", "knew", "known", "thought", "felt", "left", "found", "heard",
    "told", "began", "begun", "broken", "brought", "built", "bought", "caught",
    "chosen", "drawn", "drawn", "driven", "eaten", "fallen", "flown",
    "forgotten", "grown", "hidden", "held", "kept", "laid", "led", "lost",
    "meant", "met", "paid", "proven", "put", "read", "ridden", "risen",
    "run", "sent", "set", "shaken", "shown", "sat", "spoken", "stood",
    "struck", "sung", "sunk", "sworn", "swept", "swum", "taken", "taught",
    "torn", "thrown", "understood", "woken", "won", "worn", "written",
    "wrote", "wound", "withdrawn", "withheld", "withstood", "worked",

    # Time-related words
    "now", "then", "today", "tomorrow", "yesterday", "tonight", "morning",
    "afternoon", "evening", "night", "midnight", "noon", "dawn", "dusk",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "spring", "summer", "autumn", "winter",
    "year", "month", "week", "day", "hour", "minute", "second",
    "past", "present", "future", "age", "era", "time", "century",

    # Common adjectives that get capitalized (at start of sentence)
    "very", "really", "quite", "almost", "nearly", "just", "only",
    "also", "even", "still", "already", "always", "never",
    "often", "sometimes", "usually", "finally", "eventually",
    "however", "therefore", "meanwhile", "nevertheless", "furthermore",
    "moreover", "notwithstanding", "nonetheless", "consequently",

    # Location words that should not be characters
    "london", "paris", "new york", "berlin", "rome", "moscow", "tokyo",
    "city", "town", "village", "country", "kingdom", "empire", "republic",
    "north", "south", "east", "west", "northern", "southern", "eastern", "western",
    "sea", "ocean", "river", "lake", "mountain", "valley", "forest", "island",
    "street", "road", "avenue", "square", "bridge", "gate", "tower",
    "house", "room", "hall", "chamber", "garden", "court", "yard",
    "port", "harbor", "bay", "cape", "coast", "shore", "bank",

    # Title/role words
    "mr", "mrs", "ms", "miss", "dr", "prof", "sir", "lord", "lady",
    "king", "queen", "prince", "princess", "duke", "duchess", "count",
    "captain", "major", "colonel", "general", "lieutenant", "sergeant",
    "doctor", "professor", "reverend", "father", "mother", "brother", "sister",

    # Ordinal/cardinal number words
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
    "ninth", "tenth", "last", "next", "previous", "final",

    # Misc common words that get capitalized
    "yes", "no", "ok", "okay", "well", "oh", "ah", "alas", "indeed",
    "sure", "fine", "good", "great", "sorry", "please", "thanks",
    "hello", "goodbye", "farewell", "welcome", "dear", "my", "let",
    "tell", "ask", "see", "look", "find", "make", "take", "give",
    "come", "go", "get", "put", "set", "keep", "hold", "know",
    "think", "say", "speak", "talk", "tell", "hear", "feel",
    "like", "love", "hate", "hope", "wish", "want", "need",
    "must", "shall", "will", "can", "may", "might", "could", "would", "should",

    # Quantifiers
    "all", "each", "every", "both", "few", "many", "some", "any",
    "much", "more", "most", "several", "plenty", "enough", "little",
    "less", "least", "such", "certain", "various", "numerous",

    # Interrogatives
    "what", "when", "where", "why", "how", "who", "whom", "whose", "which",

    # Articles and misc
    "per", "via", "versus", "vs", "etc", "ie", "eg",
    "chapter", "part", "book", "volume", "section", "act", "scene",
    "introduction", "preface", "appendix", "index", "contents",
    "note", "notes", "footnote", "reference", "bibliography",

    # Additional filler words that commonly get extracted
    "poor", "dear", "old", "young", "good", "bad", "new", "next",
    "yet", "soon", "already", "away", "back", "forward", "down",
    "up", "off", "out", "in", "here", "there", "everywhere",
    "somewhere", "anywhere", "nowhere", "everyone", "someone",
    "anyone", "no one", "everything", "something", "anything", "nothing",
    "don", "dont", "can't", "cant", "won't", "wont", "isn't", "isnt",
    "aren't", "arent", "wasn't", "wasnt", "weren't", "werent", "haven't",
    "havent", "hasn't", "hasnt", "hadn't", "hadnt", "doesn't", "doesnt",
    "didn't", "didnt", "couldn't", "couldnt", "shouldn't", "shouldnt",
    "wouldn't", "wouldnt", "mustn't", "mustnt",
    "upon", "unto", "throughout", "amongst", "amidst", "whilst",
    "thou", "thee", "thy", "thine", "ye", "hence", "thence", "whence",
    "thenceforth", "henceforth", "hereafter", "thereafter",
}


# Words that are often extracted as participants but are actually locations
LOCATION_WORDS: Set[str] = {
    "london", "paris", "rome", "berlin", "moscow", "madrid", "vienna",
    "washington", "new york", "boston", "chicago", "san francisco",
    "bombay", "calcutta", "delhi", "madras", "chennai", "mumbai",
    "beijing", "shanghai", "tokyo", "kyoto", "seoul",
    "england", "france", "germany", "italy", "spain", "russia", "china",
    "india", "japan", "america", "britain", "europe", "asia",
    "athens", "sparta", "troy", "cairo", "alexandria", "jerusalem",
    "damascus", "baghdad", "constantinople", "istanbul",
    "suez", "aden", "brindisi", "calcutta", "bombay", "singapore",
    "hong kong", "shanghai", "yokohama", "san francisco",
    "new york", "boston", "philadelphia", "baltimore",
}


# Words that are actually locations but start-of-sentence capitalized
SENTENCE_START_WORDS: Set[str] = {
    "the", "this", "that", "these", "those", "it", "he", "she", "they",
    "we", "i", "you", "there", "here", "when", "where", "what", "why",
    "how", "who", "which", "whose", "whom", "after", "before", "while",
    "during", "since", "until", "because", "although", "though",
    "if", "unless", "when", "wherever", "whenever", "as", "so",
    "and", "but", "or", "nor", "yet", "for", "now", "then",
    "however", "therefore", "meanwhile", "nevertheless",
    "thus", "hence", "still", "already", "finally",
    "suddenly", "abruptly", "quickly", "slowly", "carefully",
    "once", "later", "soon", "again", "also", "even", "just",
    "only", "really", "quite", "almost", "nearly",
    "one", "two", "three", "four", "five", "first", "second",
    "many", "much", "some", "any", "all", "every", "each",
    "no", "not", "never", "always", "often", "sometimes",
    "poor", "dear", "good", "great", "old", "young",
}


class ParticipantCleaner:
    """Cleans participant lists in NarrativeFragments by removing
    non-character entries."""

    def __init__(self):
        self.stop_words = {w.lower() for w in STOP_WORDS}
        self.location_words = {w.lower() for w in LOCATION_WORDS}
        self.sentence_start_words = {w.lower() for w in SENTENCE_START_WORDS}
        self._known_characters_per_book: Dict[str, Set[str]] = {}
        self._book_specific_characters: Dict[str, Counter] = {}
        self.stats = {
            "total_participants_checked": 0,
            "invalid_removed": 0,
            "fragments_cleaned": 0,
            "fragments_seen": 0,
            "removed_by_reason": Counter(),
            "most_removed": Counter(),
        }

    def load_known_characters(self, fragments: List[NarrativeFragment]):
        """Extract known characters from fragment data, building per-book profiles."""
        book_char_counts: Dict[str, Counter] = defaultdict(Counter)

        for frag in fragments:
            book = frag.source_book
            for p in frag.participants:
                cleaned = p.strip().title()
                if cleaned and len(cleaned) > 1:
                    book_char_counts[book][cleaned] += 1

        self._book_specific_characters = dict(book_char_counts)

        # For each book, keep names that appear frequently and pass name checks
        for book, counts in book_char_counts.items():
            total = sum(counts.values())
            threshold = max(3, total * 0.005)  # 0.5% threshold
            characters = set()
            for name, count in counts.items():
                if count >= threshold and self._is_valid_character_name(name):
                    characters.add(name)
            self._known_characters_per_book[book] = characters

        logger.info(
            f"Loaded known characters for {len(self._known_characters_per_book)} books"
        )

    def _is_valid_character_name(self, name: str) -> bool:
        """Check if a name looks like a valid character name."""
        name_lower = name.lower()

        # Must be at least 2 characters
        if len(name) < 2:
            return False

        # Must contain at least one letter
        if not any(c.isalpha() for c in name):
            return False

        # Must not be a stop word
        if name_lower in self.stop_words:
            return False

        # Must not be a location word
        if name_lower in self.location_words:
            return False

        # Must not be a sentence-start word
        if name_lower in self.sentence_start_words:
            return False

        # Must start with uppercase (proper name)
        if not name[0].isupper():
            return False

        # Single-letter names are suspect (unless it's a known initial like "J.")
        if len(name) == 1 and name != "I":
            return False

        # If it looks like all-caps (acronym), skip
        if len(name) > 1 and all(c.isupper() or not c.isalpha() for c in name):
            return False

        # Remove trailing punctuation
        name_clean = name.rstrip(".!?,;:")

        if name_clean != name:
            return self._is_valid_character_name(name_clean)

        return True

    def _is_participant_valid(
        self, name: str, text: str, known_characters: Set[str]
    ) -> tuple:
        """Check if a participant entry is valid.
        Returns (is_valid, reason)."""
        name_stripped = name.strip()
        name_lower = name_stripped.lower()

        # Empty or whitespace
        if not name_stripped:
            return False, "empty"

        # Single character non-alpha
        if len(name_stripped) == 1 and not name_stripped.isalpha():
            return False, "single_non_alpha"

        # Check exact stop words
        if name_lower in self.stop_words:
            return False, "stop_word"

        # Check location words
        if name_lower in self.location_words:
            return False, "location_word"

        # Check if it's a known character
        if known_characters and name_stripped.title() in known_characters:
            return True, "known_character"

        # If it appears in text, check if it looks like a valid name
        # Must start with capital letter
        if not name_stripped[0].isupper():
            return False, "not_capitalized"

        # Skip single short words that are common
        if len(name_stripped) <= 2 and name_stripped[0].isupper():
            # Allow two-letter initials like "Dr" (but those are in stop words)
            if name_stripped in {"Dr", "Mr", "Mrs", "Ms", "St", "Mt", "No"}:
                return False, "abbreviation"
            if name_lower not in {"jo", "meg", "amy", "beth", "tom", "ed",
                                  "jim", "sam", "ben", "max", "lee", "kai",
                                  "li", "wu", "xi", "ma", "bo"}:
                # Check if it appears in text as a likely character
                if known_characters:
                    return False, "unlikely_short_name"

        # If the name appears in text but only as the start of a sentence,
        # or is a common word, it might be invalid
        if text:
            # Check if this word appears mid-sentence (not at start)
            # If it's only found at sentence starts, it's likely not a character
            if len(name_stripped.split()) == 1:
                pattern = re.compile(
                    r'(?<![.!?]\s)' + re.escape(name_stripped) + r'(?![a-zA-Z])'
                )
                mid_sentence_match = pattern.search(text)

                start_pattern = re.compile(
                    r'(?:^|[.!?]\s+)' + re.escape(name_stripped) + r'(?![a-zA-Z])'
                )
                start_match = start_pattern.search(text)

                if not mid_sentence_match and start_match:
                    # Only at sentence start - likely not a character unless known
                    if known_characters and name_stripped.title() not in known_characters:
                        return False, "sentence_start_only"

        # If it's a long phrase (more than 3 words), likely not a character name
        parts = name_stripped.split()
        if len(parts) > 4:
            return False, "too_long"

        # Numerical or mixed
        if any(c.isdigit() for c in name_stripped):
            return False, "contains_digit"

        return True, "valid"

    def clean_fragment(
        self, frag: NarrativeFragment, known_characters: Optional[Set[str]] = None
    ) -> List[str]:
        """Clean a single fragment's participant list. Returns the cleaned list."""
        if known_characters is None:
            known_characters = self._known_characters_per_book.get(
                frag.source_book, set()
            )

        self.stats["fragments_seen"] += 1
        cleaned = []
        removed = []

        for participant in frag.participants:
            self.stats["total_participants_checked"] += 1
            is_valid, reason = self._is_participant_valid(
                participant, frag.text, known_characters
            )

            if is_valid:
                cleaned.append(participant)
            else:
                removed.append((participant, reason))
                self.stats["invalid_removed"] += 1
                self.stats["removed_by_reason"][reason] += 1
                self.stats["most_removed"][participant.lower()] += 1

        if removed:
            self.stats["fragments_cleaned"] += 1

        frag.participants = cleaned
        return cleaned

    def clean_fragments(
        self, fragments: List[NarrativeFragment]
    ) -> List[NarrativeFragment]:
        """Clean all fragments in a list. Returns modified fragments."""
        self.load_known_characters(fragments)

        for frag in fragments:
            self.clean_fragment(frag)

        logger.info(
            f"Participant cleanup: {self.stats['fragments_seen']} fragments, "
            f"{self.stats['total_participants_checked']} participants, "
            f"{self.stats['invalid_removed']} removed "
            f"({self.stats['fragments_cleaned']} fragments affected)"
        )

        return fragments

    def get_stats(self) -> Dict:
        """Get cleanup statistics."""
        stats = dict(self.stats)
        stats["removed_by_reason"] = dict(self.stats["removed_by_reason"])
        stats["most_removed"] = {
            name: count
            for name, count in self.stats["most_removed"].most_common(20)
        }
        if self.stats["total_participants_checked"] > 0:
            stats["removal_rate"] = round(
                self.stats["invalid_removed"]
                / self.stats["total_participants_checked"]
                * 100,
                2,
            )
        # Calculate invalid rate (rate at which participants are invalid)
        if self.stats["total_participants_checked"] > 0:
            stats["invalid_rate"] = round(
                self.stats["invalid_removed"]
                / self.stats["total_participants_checked"]
                * 100,
                2,
            )
        else:
            stats["invalid_rate"] = 0.0
        return stats
