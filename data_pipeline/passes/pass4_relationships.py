from typing import List, Dict, Optional, Set, Tuple
import re
import logging
from collections import defaultdict, Counter

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category


logger = logging.getLogger(__name__)


# Relationship type definitions with patterns and categories
RELATIONSHIP_PATTERNS: Dict[str, Dict] = {
    "betrayals": {
        "patterns": [
            r'\bbetray(?:al|ed|s|ing)?\b', r'\btraitor\b', r'\btreacher(?:y|ous)\b',
            r'\bbackstab(?:bed|bing|s)?\b', r'\bdeceive(?:d|s)?\b',
            r'\bdouble.cross(?:ed|ing|es)?\b', r'\bsell.?out\b',
            r'\bturn(?:ed|ing)?\s+against\b', r'\bbroken\s+trust\b',
            r'\bfaithless\b', r'\babandoned\b', r'\bforsook\b', r'\bforsaken\b',
            r'\blied to\b', r'\btricked\b', r'\bdeceived\b', r'\bmisled\b',
            r'\bdeception\b', r'\bperfidy\b', r'\btreacherous\b',
        ],
        "category": Category.BETRAYALS,
        "weight": 0.95,
    },
    "rivalries": {
        "patterns": [
            r'\brival(?:s|ry|ries)?\b', r'\badversar(?:y|ies)\b',
            r'\bcompetitor(?:s)?\b', r'\bnemesis\b', r'\bopponent(?:s)?\b',
            r'\bsworn\s+enem(?:y|ies)\b', r'\bbitter\s+enem(?:y|ies)\b',
            r'\bhated\b', r'\bdespised\b', r'\bloathed\b', r'\bdisdained\b',
            r'\bantagonist(?:s)?\b', r'\bfought\b', r'\bopposed\b',
            r'\benem(?:y|ies)\b', r'\bfoe(?:s)?\b', r'\barchrival(?:s)?\b',
        ],
        "category": Category.RIVALRIES,
        "weight": 0.85,
    },
    "romances": {
        "patterns": [
            r'\blover(?:s)?\b', r'\bbeloved\b', r'\bsweetheart(?:s)?\b',
            r'\bparamour(?:s)?\b', r'\bin\s+love\b', r'\bromance(?:s)?\b',
            r'\bpassionate\b', r'\bintimate\b', r'\baffair(?:s)?\b',
            r'\bcourtship(?:s)?\b', r'\bromantic\b', r'\bloved\b',
            r'\bdarling\b', r'\bdearest\b', r'\bmy\s+love\b', r'\bmy\s+heart\b',
            r'\bkissed\b', r'\bembraced\b', r'\bcaressed\b',
            r'\bflirt(?:ed|ing|s)?\b', r'\bwooed\b', r'\bcourt(?:ed|ing|ship)?\b',
        ],
        "category": Category.ROMANCES,
        "weight": 0.85,
    },
    "family_relationships": {
        "patterns": [
            r'\bmother(?:s)?\b', r'\bfather(?:s)?\b', r'\bbrother(?:s)?\b',
            r'\bsister(?:s)?\b', r'\bson(?:s)?\b', r'\bdaughter(?:s)?\b',
            r'\bparent(?:s)?\b', r'\bchild(?:ren)?\b', r'\bsibling(?:s)?\b',
            r'\buncle(?:s)?\b', r'\baunt(?:s)?\b', r'\bcousin(?:s)?\b',
            r'\bgrandfather(?:s)?\b', r'\bgrandmother(?:s)?\b',
            r'\bgrandson(?:s)?\b', r'\bgranddaughter(?:s)?\b',
            r'\bfamily\b', r'\brelative(?:s)?\b', r'\bkin\b',
            r'\bblood\b', r'\bancestor(?:s)?\b', r'\bdescendant(?:s)?\b',
            r'\bcherished\b', r'\bnephew(?:s)?\b', r'\bniece(?:s)?\b',
            r'\bhusband(?:s)?\b', r'\bwife\b', r'\bwives\b',
            r'\bspouse(?:s)?\b', r'\bmarried\b',
        ],
        "category": Category.FAMILY_RELATIONSHIPS,
        "weight": 0.80,
    },
    "friendships": {
        "patterns": [
            r'\bfriend(?:s)?\b', r'\bbudd(?:y|ies)\b', r'\bpal(?:s)?\b',
            r'\bcomrade(?:s)?\b', r'\bally\b', r'\ballies\b',
            r'\bcompanion(?:s)?\b', r'\bconfidant(?:e|s)?\b',
            r'\bclose\s+friend(?:s)?\b', r'\bbest\s+friend(?:s)?\b',
            r'\bfriendly\b', r'\bfriendship(?:s)?\b',
            r'\bbefriended\b', r'\bstood\s+by\b', r'\bstood\s+with\b',
            r'\bside\s+by\s+side\b',
        ],
        "category": Category.FRIENDSHIPS,
        "weight": 0.80,
    },
    "mentor_relationships": {
        "patterns": [
            r'\bmentor(?:s|ed|ing)?\b', r'\bteacher(?:s)?\b', r'\bmaster(?:s)?\b',
            r'\bapprentice(?:s)?\b', r'\bstudent(?:s)?\b', r'\bguide(?:d|s)?\b',
            r'\bguru(?:s)?\b', r'\btrainer(?:s)?\b', r'\bcoach(?:es|ed|ing)?\b',
            r'\bproteg[ée](?:s)?\b', r'\bdisciple(?:s)?\b', r'\bpupil(?:s)?\b',
            r'\btutor(?:s|ed|ing)?\b', r'\btaught\b', r'\bguided\b',
            r'\bunder\s+(?:his|her)\s+(?:tutelage|guidance)\b',
        ],
        "category": Category.MENTOR_RELATIONSHIPS,
        "weight": 0.80,
    },
}


# Additional relationship detection keywords by verb
VERB_RELATIONSHIP_MAP: Dict[str, str] = {
    "loved": "romances",
    "hated": "rivalries",
    "trusted": "friendships",
    "betrayed": "betrayals",
    "admired": "mentor_relationships",
    "respected": "mentor_relationships",
    "feared": "rivalries",
    "envied": "rivalries",
    "despised": "rivalries",
    "cherished": "family_relationships",
    "protected": "family_relationships",
    "abandoned": "betrayals",
    "supported": "friendships",
    "opposed": "rivalries",
    "befriended": "friendships",
    "mentored": "mentor_relationships",
    "guided": "mentor_relationships",
    "taught": "mentor_relationships",
}


# Dialogue patterns that indicate relationships
DIALOGUE_RELATIONSHIP_INDICATORS: List[Tuple[str, str, float]] = [
    (r'(?i)(?:my\s+dear|my\s+love|my\s+darling|my\s+sweet)', "romances", 0.85),
    (r'(?i)(?:father|mother|brother|sister|son|daughter|uncle|aunt|cousin)', "family_relationships", 0.90),
    (r'(?i)(?:my\s+friend|my\s+old\s+friend|my\s+dearest\s+friend)', "friendships", 0.85),
    (r'(?i)(?:you\s+traitor|you\s+betrayed|how\s+could\s+you)', "betrayals", 0.80),
    (r'(?i)(?:sir|ma\'am|master|mistress|teacher|sensei)', "mentor_relationships", 0.60),
    (r'(?i)(?:i\s+hate\s+you|i\s+loathe\s+you|you\s+are\s+my\s+enemy)', "rivalries", 0.85),
]


# Proximity/emotional indicators for implied relationships
EMOTIONAL_RELATIONSHIP_PATTERNS: Dict[str, List[str]] = {
    "romances": ["embrace", "caress", "tender", "affection", "passion", "desire", "yearning"],
    "rivalries": ["anger", "fury", "resentment", "bitterness", "contempt", "scorn"],
    "friendships": ["warmth", "camaraderie", "ease", "comfort", "trust", "loyalty"],
    "family_relationships": ["duty", "obligation", "heritage", "lineage", "ancestry"],
    "betrayals": ["hurt", "pain", "disappointment", "shock", "disbelief", "deceit"],
    "mentor_relationships": ["respect", "admiration", "deference", "reverence", "awe"],
}


class RelationshipExtractionPass:
    def __init__(self):
        self.relationship_verbs = list(VERB_RELATIONSHIP_MAP.keys())
        # Sort patterns by weight descending so highest confidence patterns are checked first
        self.compiled_patterns = []
        for rel_type, config in sorted(
            RELATIONSHIP_PATTERNS.items(),
            key=lambda x: -x[1]["weight"]
        ):
            self.compiled_patterns.append({
                "type": rel_type,
                "patterns": [re.compile(p) for p in config["patterns"]],
                "category": config["category"].value,
                "weight": config["weight"],
            })
        self.dialogue_indicators = [
            (re.compile(p), rel_type, strength)
            for p, rel_type, strength in DIALOGUE_RELATIONSHIP_INDICATORS
        ]
        self.stats = {
            "fragments_processed": 0,
            "relationships_detected": 0,
            "by_type": Counter(),
            "by_method": Counter(),
        }

    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            self.stats["fragments_processed"] += 1
            if not frag.relationship_type:
                self._detect_relationship(frag)

        logger.info(
            f"Relationship extraction: {self.stats['fragments_processed']} fragments, "
            f"{self.stats['relationships_detected']} relationships detected"
        )
        return fragments

    def _detect_relationship(self, frag: NarrativeFragment) -> None:
        """Detect relationship type using multiple methods."""
        text = frag.text
        if not text:
            return

        # Method 1: Check explicit relationship patterns
        rel_type, confidence = self._check_patterns(text)
        if rel_type:
            frag.relationship_type = rel_type
            frag.retrieval_tags.append(f"rel:{rel_type}")
            self.stats["relationships_detected"] += 1
            self.stats["by_type"][rel_type] += 1
            self.stats["by_method"]["pattern_match"] += 1
            # Update fragment category if it's not already set
            if not frag.category:
                frag.category = Category.RELATIONSHIPS.value
                if rel_type in [e.value for e in [
                    Category.FRIENDSHIPS, Category.RIVALRIES, Category.ROMANCES,
                    Category.FAMILY_RELATIONSHIPS, Category.MENTOR_RELATIONSHIPS,
                    Category.BETRAYALS,
                ]]:
                    frag.subcategory = rel_type
            return

        # Method 2: Check dialogue indicators
        rel_type, confidence = self._check_dialogue(text)
        if rel_type:
            frag.relationship_type = rel_type
            frag.retrieval_tags.append(f"rel:{rel_type}")
            self.stats["relationships_detected"] += 1
            self.stats["by_type"][rel_type] += 1
            self.stats["by_method"]["dialogue"] += 1
            return

        # Method 3: Check verb-based relationships
        rel_type = self._check_verbs(text)
        if rel_type:
            frag.relationship_type = rel_type
            frag.retrieval_tags.append(f"rel:{rel_type}")
            self.stats["relationships_detected"] += 1
            self.stats["by_type"][rel_type] += 1
            self.stats["by_method"]["verb_match"] += 1
            return

        # Method 4: Check emotional indicators
        rel_type = self._check_emotional(text)
        if rel_type:
            frag.relationship_type = rel_type
            frag.retrieval_tags.append(f"rel:{rel_type}")
            self.stats["relationships_detected"] += 1
            self.stats["by_type"][rel_type] += 1
            self.stats["by_method"]["emotional"] += 1
            return

    def _check_patterns(self, text: str) -> Tuple[Optional[str], float]:
        """Check text against explicit relationship patterns.
        Patterns are checked in descending weight order."""
        text_lower = text.lower()
        for config in self.compiled_patterns:
            for pattern in config["patterns"]:
                if pattern.search(text_lower):
                    return config["type"], config["weight"]
        return None, 0.0

    def _check_dialogue(self, text: str) -> Tuple[Optional[str], float]:
        """Check dialogue text for relationship indicators."""
        for pattern, rel_type, strength in self.dialogue_indicators:
            if pattern.search(text):
                return rel_type, strength
        return None, 0.0

    def _check_verbs(self, text: str) -> Optional[str]:
        """Check text for relationship verbs."""
        text_lower = text.lower()
        for verb in self.relationship_verbs:
            if verb in text_lower:
                return VERB_RELATIONSHIP_MAP[verb]
        return None

    def _check_emotional(self, text: str) -> Optional[str]:
        """Check text for emotional relationship indicators."""
        text_lower = text.lower()
        for rel_type, indicators in EMOTIONAL_RELATIONSHIP_PATTERNS.items():
            for indicator in indicators:
                if indicator in text_lower:
                    return rel_type
        return None

    def get_stats(self) -> Dict:
        """Get extraction statistics."""
        stats = dict(self.stats)
        stats["by_type"] = dict(self.stats["by_type"])
        stats["by_method"] = dict(self.stats["by_method"])
        return stats
