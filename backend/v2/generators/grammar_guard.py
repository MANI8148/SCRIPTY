"""POS-tag filter for rejecting ungrammatical generated sentences."""

from __future__ import annotations

import re

import nltk


class GrammarGuard:
    """Validates generated sentences for basic grammatical correctness.

    Uses NLTK POS tagging to reject:
    - Subject-verb agreement errors (3sg subject + base verb)
    - Determiner-noun agreement (e.g. "a apple" → "an apple")
    - Pronoun-case errors (e.g. "me went")
    Falls back to regex when NLTK tagging fails.
    """

    # Patterns that indicate grammatical errors
    _ERROR_PATTERNS: list[re.Pattern] = [
        re.compile(r"\ba\s+[aeiou][a-z]+", re.IGNORECASE),
        re.compile(r"\ban\s+[^aeiou\s][a-z]*\b", re.IGNORECASE),
        re.compile(r"\b(me|him|her|us|them)\s+(went|go|runs|said|did)\b", re.IGNORECASE),
        re.compile(r"\b(they|we|i|you|he|she|it)\s+(me|him|her|us|them)\s+\w+\b", re.IGNORECASE),
        re.compile(r"\b(these|those)\s+a\b", re.IGNORECASE),
        re.compile(r"\b(this|that)\s+[a-z]+s\b", re.IGNORECASE),
        re.compile(r"\b(is|are|was|were)\s+[a-z]+ed\b", re.IGNORECASE),
    ]

    # Number agreement: 3sg pronoun/noun must pair with 3sg verb
    _THIRD_SG_PRONOUNS = {"he", "she", "it"}
    _PLURAL_PRONOUNS = {"they", "we"}
    _THIRD_SG_VERB_SUFFIXES = {"s", "es", "ies"}
    _BASE_VERBS = {
        "go", "have", "do", "say", "make", "take", "come", "see",
        "know", "get", "give", "find", "tell", "ask", "seem",
        "feel", "try", "leave", "call", "keep", "let", "begin",
        "show", "hear", "play", "run", "move", "live", "believe",
        "hold", "bring", "happen", "write", "provide", "sit",
        "stand", "lose", "pay", "meet", "include", "continue",
        "set", "learn", "change", "lead", "understand", "watch",
        "follow", "stop", "create", "speak", "read", "allow",
        "add", "spend", "grow", "open", "walk", "win", "teach",
        "offer", "remember", "consider", "appear", "buy", "serve",
        "die", "send", "build", "stay", "fall", "cut", "reach",
        "kill", "remain", "suggest", "raise", "pass", "sell",
        "require", "report", "decide", "pull", "develop",
    }

    def validate(self, tokens: list[str]) -> bool:
        """Return True if the sentence passes all grammar checks."""
        if not tokens:
            return False

        text = " ".join(tokens)

        for pattern in self._ERROR_PATTERNS:
            if pattern.search(text):
                return False

        try:
            return self._validate_pos(tokens)
        except Exception:
            return self._validate_regex_fallback(tokens)

    def _validate_pos(self, tokens: list[str]) -> bool:
        """Validate using NLTK POS tagging."""
        if len(tokens) < 2:
            return True

        pos_tags = nltk.pos_tag(tokens)
        for i, (word, tag) in enumerate(pos_tags):
            if tag.startswith("NN") or tag.startswith("PRP"):
                if i + 1 < len(pos_tags):
                    next_word, next_tag = pos_tags[i + 1]
                    if next_tag.startswith("VB") and not next_tag.startswith("VBZ"):
                        if word.lower() in self._THIRD_SG_PRONOUNS:
                            return False

            if word.lower() in self._THIRD_SG_PRONOUNS or (tag == "NN" and tag != "NNS"):
                if i + 1 < len(pos_tags):
                    _, next_tag = pos_tags[i + 1]
                    if next_tag == "VBP":
                        return False

            if word.lower() in self._PLURAL_PRONOUNS or tag == "NNS":
                if i + 1 < len(pos_tags):
                    _, next_tag = pos_tags[i + 1]
                    if next_tag == "VBZ":
                        return False

        return True

    def _validate_regex_fallback(self, tokens: list[str]) -> bool:
        """Fallback using regex when NLTK POS tagging fails."""
        text = " ".join(tokens).lower()
        words = text.split()

        for i, word in enumerate(words):
            if word in self._THIRD_SG_PRONOUNS:
                if i + 1 < len(words):
                    next_word = words[i + 1]
                    if next_word in self._BASE_VERBS:
                        return False

        return True

    @staticmethod
    def fix_article(text: str) -> str:
        """Fix 'a' → 'an' before vowel sounds."""
        return re.sub(
            r"\ba\s+([aeiou])",
            r"an \1",
            text,
            count=0,
            flags=re.IGNORECASE,
        )
