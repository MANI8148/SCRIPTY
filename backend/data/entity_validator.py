"""
SCRIPTY - Entity Validator
Filters and validates NER-extracted entities using confidence scoring and curated allowlists.

Implements:
- Confidence score calculation (0.0-1.0) based on length, capitalization, dictionary presence
- Length validation (3-20 characters)
- Capitalization validation (proper case required)
- Dictionary check using NLTK words corpus
- Pattern matching (reject names with numbers or special characters)
- filter_entities() returning valid entities with confidence scores
- Curated allowlist fallback for rejected entities
- Performance target: <5ms per entity validation

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""
import re
import logging
from typing import Optional

from backend.data.curated_lists import CHARACTERS
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

# Minimum and maximum character lengths for valid names
_MIN_NAME_LENGTH = 3
_MAX_NAME_LENGTH = 20

# Regex pattern for valid name characters (letters, spaces, hyphens, apostrophes)
_VALID_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z\s\-'\.]*$")

# Regex to detect names that contain digits or special characters (beyond allowed set)
_INVALID_CHARS_PATTERN = re.compile(r"[0-9@#$%^&*()_+=\[\]{};:\"<>,?/\\|`~!]")

# NLTK words corpus - loaded lazily
_nltk_words_set: Optional[set] = None
_nltk_load_attempted: bool = False


def _get_nltk_words() -> set:
    """
    Lazily load the NLTK words corpus.
    Returns an empty set if NLTK is unavailable.
    """
    global _nltk_words_set, _nltk_load_attempted
    if _nltk_load_attempted:
        return _nltk_words_set or set()

    _nltk_load_attempted = True
    try:
        import nltk
        try:
            from nltk.corpus import words as nltk_words_corpus
            _nltk_words_set = set(w.lower() for w in nltk_words_corpus.words())
        except LookupError:
            # Download the corpus if not present
            nltk.download("words", quiet=True)
            from nltk.corpus import words as nltk_words_corpus
            _nltk_words_set = set(w.lower() for w in nltk_words_corpus.words())
        logger.debug(
            "NLTK words corpus loaded: %d words", len(_nltk_words_set)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("NLTK words corpus unavailable: %s", exc)
        _nltk_words_set = set()

    return _nltk_words_set or set()


class EntityValidator:
    """
    Validates NER-extracted entities using confidence scoring and curated allowlists.

    Confidence scores (0.0-1.0) are calculated based on:
    - Length appropriateness (3-20 characters)
    - Proper capitalization (first letter uppercase)
    - Absence from common English dictionary
    - Absence of digits and special characters
    - Multi-word name bonus (proper names often have multiple parts)

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    def __init__(self, strict_mode: bool = True) -> None:
        """
        Initialize the EntityValidator.

        Args:
            strict_mode: When True, apply stricter validation rules.
                         When False, allow borderline cases with lower confidence scores.
        """
        self._strict_mode = strict_mode
        # Pre-load NLTK words corpus at init time for performance
        self._dictionary_words = _get_nltk_words()
        logger.debug(
            "EntityValidator initialized",
            extra={"extra_fields": {"strict_mode": strict_mode}},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_person_name(self, name: str) -> tuple[bool, float, str]:
        """
        Validate a person name and compute its confidence score.

        Args:
            name: The person name to validate.

        Returns:
            A tuple of (is_valid, confidence_score, rejection_reason) where:
            - is_valid: True if the name passes all validation rules
            - confidence_score: Float in [0.0, 1.0] representing quality
            - rejection_reason: Empty string if valid, otherwise a description
              of why the name was rejected
        """
        return self._validate_name(name, entity_type="person")

    def validate_place_name(self, name: str) -> tuple[bool, float, str]:
        """
        Validate a place name and compute its confidence score.

        Place names follow slightly relaxed rules compared to person names:
        they may contain numbers (e.g., "Route 66") and are not checked
        against the common-word dictionary.

        Args:
            name: The place name to validate.

        Returns:
            A tuple of (is_valid, confidence_score, rejection_reason).
        """
        return self._validate_name(name, entity_type="place")

    def filter_entities(
        self, entities: list[str], entity_type: str
    ) -> list[tuple[str, float]]:
        """
        Filter a list of entities, returning only valid ones with their scores.

        When all entities are rejected, falls back to the curated allowlist
        (CHARACTERS for person entities).

        Args:
            entities: List of entity name strings to validate.
            entity_type: One of "person", "place", or "concept".

        Returns:
            List of (name, confidence_score) tuples for valid entities,
            sorted by confidence score descending.
            Falls back to curated allowlist entries (score=1.0) if all
            entities are rejected.
        """
        valid: list[tuple[str, float]] = []

        for name in entities:
            if entity_type == "place":
                is_valid, score, reason = self.validate_place_name(name)
            else:
                # Default to person validation for "person" and "concept"
                is_valid, score, reason = self.validate_person_name(name)

            if is_valid:
                valid.append((name, score))
            else:
                logger.debug(
                    "Entity rejected: %s — %s",
                    name,
                    reason,
                    extra={
                        "entity_name": name,
                        "rejection_reason": reason,
                    },
                )

        if not valid:
            # All entities rejected — use curated fallback
            logger.warning(
                "All %d entities rejected for type '%s'; using curated fallback",
                len(entities),
                entity_type,
            )
            if entity_type in ("person", "concept"):
                valid = [(name, 1.0) for name in CHARACTERS]
            # For places, return empty list (caller should handle fallback)

        # Sort by confidence score descending
        valid.sort(key=lambda x: x[1], reverse=True)
        return valid

    # ------------------------------------------------------------------
    # Internal validation logic
    # ------------------------------------------------------------------

    def _validate_name(
        self, name: str, entity_type: str
    ) -> tuple[bool, float, str]:
        """
        Core validation logic shared by person and place name validation.

        Applies rules in order of severity; returns on first hard rejection.
        Confidence score is computed from multiple weighted factors.

        Args:
            name: The name string to validate.
            entity_type: "person" or "place" — affects which rules apply.

        Returns:
            (is_valid, confidence_score, rejection_reason)
        """
        # --- Hard rejections (score = 0.0) ---

        # 1. Empty or whitespace-only
        stripped = name.strip() if name else ""
        if not stripped:
            return False, 0.0, "empty name"

        # 2. Length check (Requirement 4.2)
        name_len = len(stripped)
        if name_len < _MIN_NAME_LENGTH:
            return (
                False,
                0.0,
                f"name too short ({name_len} chars, minimum {_MIN_NAME_LENGTH})",
            )
        if name_len > _MAX_NAME_LENGTH:
            return (
                False,
                0.0,
                f"name too long ({name_len} chars, maximum {_MAX_NAME_LENGTH})",
            )

        # 3. Capitalization check — first letter must be uppercase
        if not stripped[0].isupper():
            return False, 0.0, "name does not start with uppercase letter"

        # 4. Invalid characters check (digits and special chars)
        #    Place names may contain digits (e.g., "Route 66"), so skip for places
        if entity_type != "place" and _INVALID_CHARS_PATTERN.search(stripped):
            return False, 0.0, "name contains digits or special characters"

        # 5. Pattern check — must match allowed character set
        if entity_type != "place" and not _VALID_NAME_PATTERN.match(stripped):
            return False, 0.0, "name contains invalid characters"

        # 6. Dictionary check — reject common English words (Requirement 4.3)
        #    Only applied to person names in strict mode
        if entity_type == "person":
            # Check each word in the name against the dictionary
            words_in_name = stripped.split()
            if self._strict_mode:
                # In strict mode: reject if ALL words are common dictionary words
                # (single-word names that are common words are rejected)
                if len(words_in_name) == 1:
                    if stripped.lower() in self._dictionary_words:
                        return (
                            False,
                            0.0,
                            f"name '{stripped}' is a common English dictionary word",
                        )
                else:
                    # Multi-word: reject only if every word is a common dictionary word
                    if all(w.lower() in self._dictionary_words for w in words_in_name):
                        return (
                            False,
                            0.0,
                            f"name '{stripped}' consists entirely of common English words",
                        )
            else:
                # Non-strict mode: only reject single-word names that are very common
                if len(words_in_name) == 1 and stripped.lower() in self._dictionary_words:
                    return (
                        False,
                        0.0,
                        f"name '{stripped}' is a common English dictionary word",
                    )

        # --- Confidence score calculation ---
        score = self._calculate_confidence(stripped, entity_type)

        return True, score, ""

    def _calculate_confidence(self, name: str, entity_type: str) -> float:
        """
        Calculate a confidence score (0.0-1.0) for a name that has passed
        all hard validation rules.

        Scoring factors:
        - Base score: 0.5
        - Length bonus: +0.1 if length is in the "ideal" range (4-15 chars)
        - Capitalization bonus: +0.1 if properly title-cased
        - Multi-word bonus: +0.1 if name has 2+ words (proper names often do)
        - Dictionary absence bonus: +0.1 if not in common word list (person only)
        - No special chars bonus: +0.1 if purely alphabetic (with spaces/hyphens)

        Args:
            name: The validated name string.
            entity_type: "person" or "place".

        Returns:
            Float in [0.0, 1.0].
        """
        score = 0.5  # Base score for passing hard validation

        name_len = len(name)
        words = name.split()

        # Length bonus: ideal range 4-15 characters
        if 4 <= name_len <= 15:
            score += 0.1

        # Capitalization bonus: title case (each word starts with uppercase)
        if all(w[0].isupper() for w in words if w):
            score += 0.1

        # Multi-word bonus: proper names often have first + last name
        if len(words) >= 2:
            score += 0.1

        # Dictionary absence bonus (person names only)
        if entity_type == "person":
            name_lower = name.lower()
            if name_lower not in self._dictionary_words:
                score += 0.1

        # Clean character bonus: purely alphabetic with allowed separators
        if re.match(r"^[A-Za-z][A-Za-z\s\-']*$", name):
            score += 0.1

        # Clamp to [0.0, 1.0]
        return min(1.0, max(0.0, round(score, 4)))
