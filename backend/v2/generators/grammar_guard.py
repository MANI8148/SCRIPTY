"""
SCRIPTY v2 — GrammarGuard
POS-tag filter rejects subject-verb, determiner-noun, pronoun-case errors.
Secondary regex fallback when nltk fails.
Target: 80%+ rejection of known-bad sentences.
"""
from __future__ import annotations

import re
from typing import Optional

try:
    import nltk
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class GrammarGuard:
    """
    Validates generated sentences for grammatical correctness.
    Uses NLTK POS tagging when available, falls back to regex patterns.
    """

    # Common error patterns (regex fallback)
    ERROR_PATTERNS = [
        (r"\bhe (?:is|was|has|had|does|did|can|could|will|would|should|must)\b", "subject-verb"),
        (r"\bshe (?:is|was|has|had|does|did|can|could|will|would|should|must)\b", "subject-verb"),
        (r"\bit (?:is|was|has|had|does|did|can|could|will|would|should|must)\b", "subject-verb"),
        (r"\bthey (?:am|is|was|has|had|does|did)\b", "subject-verb"),
        (r"\bwe (?:am|is|was|has|had|does|did)\b", "subject-verb"),
        (r"\ba (?:apple|orange|egg|umbrella|honest|hour)\b", "determiner-noun"),
        (r"\ban (?:book|car|dog|house|tree)\b", "determiner-noun"),
        (r"\bme (?:went|go|goes|going|am|is|was|has|had)\b", "pronoun-case"),
        (r"\bhim (?:went|go|goes|going|am|is|was|has|had)\b", "pronoun-case"),
        (r"\bher (?:went|go|goes|going|am|is|was|has|had)\b", "pronoun-case"),
        (r"\bus (?:went|go|goes|going|am|is|was|has|had)\b", "pronoun-case"),
        (r"\bthem (?:went|go|goes|going|am|is|was|has|had)\b", "pronoun-case"),
    ]

    def __init__(self):
        self._ensure_nltk_data()

    def _ensure_nltk_data(self):
        if NLTK_AVAILABLE:
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)
            try:
                nltk.data.find("taggers/averaged_perceptron_tagger")
            except LookupError:
                nltk.download("averaged_perceptron_tagger", quiet=True)

    def validate(self, tokens: list[str]) -> tuple[bool, list[str]]:
        """
        Validate a token sequence.
        Returns (is_valid, list_of_errors).
        """
        if not tokens:
            return True, []

        text = " ".join(tokens)
        errors = []

        if NLTK_AVAILABLE:
            errors.extend(self._validate_with_nltk(tokens))

        errors.extend(self._validate_with_regex(text))

        return len(errors) == 0, errors

    def _validate_with_nltk(self, tokens: list[str]) -> list[str]:
        errors = []
        try:
            tagged = pos_tag(tokens)
            for i, (word, tag) in enumerate(tagged):
                if tag.startswith("NN") and i > 0:
                    prev_word, prev_tag = tagged[i-1]
                    if prev_tag in ("DT", "PRP$") and prev_word.lower() == "a" and word[0].lower() in "aeiou":
                        errors.append(f"determiner-noun: 'a {word}' should be 'an {word}'")
                    elif prev_tag in ("DT", "PRP$") and prev_word.lower() == "an" and word[0].lower() not in "aeiou":
                        errors.append(f"determiner-noun: 'an {word}' should be 'a {word}'")

                if tag.startswith("VB") and i > 0:
                    prev_word, prev_tag = tagged[i-1]
                    if prev_tag == "PRP":
                        pronoun = prev_word.lower()
                        verb = word.lower()
                        if pronoun in ("he", "she", "it") and verb not in ("is", "was", "has", "had", "does", "did", "goes", "go", "can", "could", "will", "would", "should", "must"):
                            errors.append(f"subject-verb: '{pronoun} {verb}' agreement error")
                        elif pronoun in ("they", "we") and verb in ("is", "was", "has", "had", "does", "did", "goes"):
                            errors.append(f"subject-verb: '{pronoun} {verb}' agreement error")

        except Exception:
            pass
        return errors

    def _validate_with_regex(self, text: str) -> list[str]:
        errors = []
        for pattern, error_type in self.ERROR_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"{error_type}: pattern matched in '{text[:50]}...'")
        return errors

    def validate_and_fix(self, tokens: list[str]) -> list[str]:
        """Validate and attempt to fix common errors."""
        is_valid, errors = self.validate(tokens)
        if is_valid:
            return tokens

        text = " ".join(tokens)
        fixes = [
            (r"\ba (apple|orange|egg|umbrella|honest|hour)\b", r"an \1"),
            (r"\ban (book|car|dog|house|tree)\b", r"a \1"),
            (r"\bme (went|go|goes|going|am|is|was|has|had)\b", r"I \1"),
            (r"\bhim (went|go|goes|going|am|is|was|has|had)\b", r"he \1"),
            (r"\bher (went|go|goes|going|am|is|was|has|had)\b", r"she \1"),
            (r"\bus (went|go|goes|going|am|is|was|has|had)\b", r"we \1"),
            (r"\bthem (went|go|goes|going|am|is|was|has|had)\b", r"they \1"),
        ]

        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text.split()