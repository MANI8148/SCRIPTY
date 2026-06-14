"""Unified narrative quality metrics for SCRIPTY v2.

Every metric is a pure function taking raw text and returning a float.
Thresholds, word lists, and constants are defined once here and imported
by tests, benchmarks, and validation audits.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import ClassVar


# ═══════════════════════════════════════════════════════════════════════
# Word lists — single source of truth
# ═══════════════════════════════════════════════════════════════════════

SHOW_VERBS: set[str] = {
    "clench", "clenched", "clenching",
    "strike", "struck", "striking",
    "reach", "reached", "reaching",
    "turn", "turned", "turning",
    "step", "stepped", "stepping",
    "grasp", "grasped", "grasping",
    "lunge", "lunged", "lunging",
    "press", "pressed", "pressing",
    "clutch", "clutched", "clutching",
    "shove", "shoved", "shoving",
    "grab", "grabbed", "grabbing",
    "pull", "pulled", "pulling",
    "push", "pushed", "pushing",
    "kick", "kicked", "kicking",
    "punch", "punched", "punching",
    "swing", "swung", "swinging",
    "stride", "strode", "striding",
    "crouch", "crouched", "crouching",
    "duck", "ducked", "ducking",
    "dive", "dove", "diving",
    "spin", "spun", "spinning",
    "snap", "snapped", "snapping",
    "slam", "slammed", "slamming",
    "block", "blocked", "blocking",
    "face", "faced", "facing",
    "examine", "examined", "examining",
    "peer", "peered", "peering",
    "scrutinize", "scrutinized", "scrutinizing",
    "dart", "darted", "darting",
    "slip", "slipped", "slipping",
    "follow", "followed", "following",
    "chase", "chased", "chasing",
    "track", "tracked", "tracking",
    "shield", "shielded", "shielding",
    "rummage", "rummaged", "rummaging",
    "scan", "scanned", "scanning",
    "draw", "drew", "drawing",
    "watch", "watched", "watching",
    "coil", "coiled", "coiling",
    "tremble", "trembled", "trembling",
    "slump", "slumped", "slumping",
    "shift", "shifted", "shifting",
    "crack", "cracked", "cracking",
    "trace", "traced", "tracing",
    "narrow", "narrowed", "narrowing",
    "plant", "planted", "planting",
    "fold", "folded", "folding",
    "adjust", "adjusted", "adjusting",
    "glance", "glanced", "glancing",
    "lift", "lifted", "lifting",
    "flinch", "flinched", "flinching",
    "hiss", "hissed", "hissing",
    "snarl", "snarled", "snarling",
    "growl", "growled", "growling",
    "whisper", "whispered", "whispering",
    "murmur", "murmured", "murmuring",
    "mutter", "muttered", "muttering",
    "vow", "vowed", "vowing",
    "declare", "declared", "declaring",
    "soothe", "soothed", "soothing",
    "shudder", "shuddered", "shuddering",
    "frown", "frowned", "frowning",
    "glare", "glared", "glaring",
    "scowl", "scowled", "scowling",
    "beam", "beamed", "beaming",
    "gasp", "gasped", "gasping",
    "sigh", "sighed", "sighing",
    "weep", "wept", "weeping",
    "grin", "grinned", "grinning",
}

TELL_VERBS: set[str] = {
    "is", "was", "were", "felt", "seemed", "appeared",
    "became", "looked", "sounded", "remained", "stayed",
}

EMOTION_BEHAVIOR: set[str] = {
    "clenched", "trembled", "shook", "froze", "gasped", "sighed",
    "flinched", "shuddered", "wept", "laughed", "smiled", "frowned",
    "glared", "glowered", "beamed", "scowled", "grinned",
}

EMOTION_STATE: set[str] = {
    "angry", "sad", "happy", "scared", "afraid", "worried", "anxious",
    "excited", "jealous", "guilty", "ashamed", "proud", "hurt", "lonely",
    "furious", "terrified", "delighted", "grief", "hopeful",
}

SIMULATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"drum.*(rhythm|fingers|table)"),
    re.compile(r"picked.*(lint|thread|invisible)"),
    re.compile(r"the weight of.*the"),
    re.compile(r"stood in silence"),
    re.compile(r"it was not what (he|she|they) expected"),
]

CONFLICT_KEYWORDS: list[str] = [
    "anger", "fight", "conflict", "tension", "enemy", "danger",
    "threat", "struggle", "confront", "battle", "war", "attack",
    "resistance", "hostile", "vengeance", "grudge",
]

EMOTION_KEYWORDS: list[str] = [
    "fear", "joy", "sad", "anger", "love", "hate", "hope",
    "despair", "anxiety", "calm", "peace", "grief",
    "sorrow", "passion", "dread", "longing",
]

DEFAULT_KNOWN_NAMES: set[str] = {
    "Arjun", "Maya", "Kiran", "Ravi", "Priya", "Vikram",
    "Ananya", "Raj", "Neha", "Aarav", "Ishaan", "Sita",
    "Ram", "Lakshmi", "Devi", "Krishna", "Shiva", "Durga",
    "Ganesh", "Kali", "Parvati", "Lakshman", "Bharat",
    "Satya", "Ahimsa", "Dharma", "Karma", "Moksha",
}


# ═══════════════════════════════════════════════════════════════════════
# Named thresholds
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MetricThresholds:
    dialogue_density: float = 0.15
    show_vs_tell: float = 3.0
    unique_sentence_starts: float = 0.85
    emotional_expression: float = 0.5
    repetition_rate: float = 0.10
    coherence: float = 0.80
    simulation_pattern_per_story: int = 2
    ttr_min: float = 0.30
    max_dialogue_lines_per_story: int = 5
    word_count_min: int = 50


THRESHOLDS = MetricThresholds()

# For "invert" metrics where lower is better
INVERT_METRICS: set[str] = {"repetition_rate", "simulation_patterns"}


# ═══════════════════════════════════════════════════════════════════════
# Result container
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class MetricsResult:
    dialogue_density: float = 0.0
    show_vs_tell: float = 0.0
    unique_sentence_starts: float = 0.0
    emotional_expression: float = 0.0
    repetition_rate: float = 0.0
    coherence: float = 0.0
    simulation_patterns: int = 0
    type_token_ratio: float = 0.0
    word_count: int = 0
    dialogue_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    unique_words: int = 0

    def passed(self, threshold: MetricThresholds = THRESHOLDS) -> dict[str, bool]:
        return {
            "dialogue_density": self.dialogue_density >= threshold.dialogue_density,
            "show_vs_tell": self.show_vs_tell >= threshold.show_vs_tell,
            "unique_sentence_starts": self.unique_sentence_starts >= threshold.unique_sentence_starts,
            "emotional_expression": self.emotional_expression >= threshold.emotional_expression,
            "repetition_rate": self.repetition_rate <= threshold.repetition_rate,
            "coherence": self.coherence >= threshold.coherence,
            "simulation_patterns": self.simulation_patterns <= threshold.simulation_pattern_per_story,
            "type_token_ratio": self.type_token_ratio >= threshold.ttr_min,
            "word_count": self.word_count >= threshold.word_count_min,
        }


# ═══════════════════════════════════════════════════════════════════════
# Metric functions — pure, text-in float-out
# ═══════════════════════════════════════════════════════════════════════


def word_count(text: str) -> int:
    return len(text.split())


def sentence_count(text: str) -> int:
    return len(re.split(r"(?<=[.!?])\s+", text.strip())) if text.strip() else 0


def unique_words(text: str) -> int:
    return len({w.lower().strip(".,!?;:\"'()[]-") for w in text.split()})


def type_token_ratio(text: str) -> float:
    """Unique words / total words."""
    wc = word_count(text)
    return unique_words(text) / max(wc, 1)


def avg_sentence_length(text: str) -> float:
    """Mean words per sentence."""
    sc = sentence_count(text)
    return word_count(text) / max(sc, 1)


def dialogue_count(text: str) -> int:
    """Count of quoted dialogue lines."""
    return len(re.findall(r'[\u201c"]([^\u201d"]*)[\u201d"]', text))


def dialogue_density(text: str) -> float:
    """Quoted words / total words."""
    total = word_count(text)
    if total == 0:
        return 0.0
    quoted_words = sum(
        len(q.split())
        for q in re.findall(r'[\u201c"]([^\u201d"]*)[\u201d"]', text)
    )
    return quoted_words / total


def show_vs_tell(text: str) -> float:
    """Concrete action verbs / abstract state verbs."""
    show = 0
    tell = 0
    for w in text.lower().split():
        wc = w.strip(".,!?;:\"'()[]-")
        if wc in SHOW_VERBS:
            show += 1
        elif wc in TELL_VERBS:
            tell += 1
    if tell == 0:
        return float(show) if show > 0 else 0.0
    return show / tell


def unique_sentence_starts(text: str) -> float:
    """Distinct first-3-word starts / total sentences."""
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    starts: list[str] = []
    for sent in sents:
        sent = sent.strip()
        if not sent:
            continue
        words = sent.split()
        if len(words) >= 3:
            starts.append(" ".join(words[:3]).lower())
        elif len(words) >= 1:
            starts.append(" ".join(words).lower())
    if not starts:
        return 1.0
    return len(set(starts)) / len(starts)


def emotional_expression(text: str) -> float:
    """Emotional behavior words / emotional state words."""
    behavior = 0
    state = 0
    for w in text.lower().split():
        wc = w.strip(".,!?;:\"'()[]-")
        if wc in EMOTION_BEHAVIOR:
            behavior += 1
        elif wc in EMOTION_STATE:
            state += 1
    if state == 0:
        return float(behavior) if behavior > 0 else 0.0
    return behavior / state


def repetition_rate(text: str) -> float:
    """Repeated bigrams / total bigrams."""
    words = text.lower().split()
    bigrams: list[tuple[str, str]] = []
    for i in range(len(words) - 1):
        if len(words[i]) < 2 or len(words[i + 1]) < 2:
            continue
        bigrams.append((words[i], words[i + 1]))
    if not bigrams:
        return 0.0
    counts: Counter = Counter(bigrams)
    repeated = sum(1 for c in counts.values() if c > 1)
    return repeated / len(bigrams)


def coherence(text: str, known_names: set[str] | None = None) -> float:
    """Entity reference consistency — ratio of sentences that reference
    already-established named entities."""
    names = known_names or DEFAULT_KNOWN_NAMES
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sents) < 2:
        return 1.0
    established: set[str] = set()
    consistent = 0
    for sent in sents:
        found = set(re.findall(r"\b[A-Z][a-z]+\b", sent)) & names
        if found:
            if established:
                consistent += 1
            established.update(found)
    return consistent / max(len(sents) - 1, 1)


def simulation_pattern_count(text: str) -> int:
    """Count of mechanical/overused narrative patterns."""
    return sum(
        1 for pat in SIMULATION_PATTERNS for _ in pat.finditer(text.lower())
    )


def bigram_overlap_ratio(text: str) -> float:
    """1.0 - (unique_bigrams / total_bigrams). Higher = more repetition."""
    words = text.split()
    if len(words) < 2:
        return 0.0
    bigrams = {f"{words[i].lower()} {words[i+1].lower()}" for i in range(len(words) - 1)}
    total_possible = len(words) - 1
    return 1.0 - (len(bigrams) / max(total_possible, 1))


def trigram_jaccard(text_a: str, text_b: str) -> float:
    """Set intersection / set union of character trigrams."""
    def _trigrams(t: str) -> set[str]:
        words = t.lower().split()
        return {" ".join(words[i:i+3]) for i in range(len(words) - 2)}
    a = _trigrams(text_a)
    b = _trigrams(text_b)
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def compute_divergence(text_a: str, text_b: str) -> float:
    """1.0 - Jaccard(text_a, text_b). Higher = more divergent."""
    def _token_set(t: str) -> set[str]:
        return {w.lower().strip(".,!?;:\"'()[]-") for w in t.split() if len(w) >= 3}
    a = _token_set(text_a)
    b = _token_set(text_b)
    union = a | b
    if not union:
        return 0.0
    return 1.0 - (len(a & b) / len(union))


def conflict_keyword_count(text: str) -> int:
    return sum(1 for kw in CONFLICT_KEYWORDS if kw in text.lower())


def emotion_keyword_count(text: str) -> int:
    return sum(1 for kw in EMOTION_KEYWORDS if kw in text.lower())


# ═══════════════════════════════════════════════════════════════════════
# Composite runner
# ═══════════════════════════════════════════════════════════════════════

def measure_all(text: str) -> MetricsResult:
    """Run all metrics on a single text and return a structured result."""
    return MetricsResult(
        dialogue_density=dialogue_density(text),
        show_vs_tell=show_vs_tell(text),
        unique_sentence_starts=unique_sentence_starts(text),
        emotional_expression=emotional_expression(text),
        repetition_rate=repetition_rate(text),
        coherence=coherence(text),
        simulation_patterns=simulation_pattern_count(text),
        type_token_ratio=type_token_ratio(text),
        word_count=word_count(text),
        dialogue_count=dialogue_count(text),
        sentence_count=sentence_count(text),
        avg_sentence_length=avg_sentence_length(text),
        unique_words=unique_words(text),
    )


def measure_batch(texts: list[str]) -> MetricsResult:
    """Run all metrics across a batch of texts and return averages."""
    results = [measure_all(t) for t in texts]
    n = len(results)
    if n == 0:
        return MetricsResult()
    return MetricsResult(
        dialogue_density=sum(r.dialogue_density for r in results) / n,
        show_vs_tell=sum(r.show_vs_tell for r in results) / n,
        unique_sentence_starts=sum(r.unique_sentence_starts for r in results) / n,
        emotional_expression=sum(r.emotional_expression for r in results) / n,
        repetition_rate=sum(r.repetition_rate for r in results) / n,
        coherence=sum(r.coherence for r in results) / n,
        simulation_patterns=int(round(sum(r.simulation_patterns for r in results) / n)),
        type_token_ratio=sum(r.type_token_ratio for r in results) / n,
        word_count=int(round(sum(r.word_count for r in results) / n)),
        dialogue_count=int(round(sum(r.dialogue_count for r in results) / n)),
        sentence_count=int(round(sum(r.sentence_count for r in results) / n)),
        avg_sentence_length=sum(r.avg_sentence_length for r in results) / n,
        unique_words=int(round(sum(r.unique_words for r in results) / n)),
    )
