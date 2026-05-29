"""
Unit tests for EntityValidator (Tasks 3.1 and 3.2)

Tests cover:
- validate_person_name: length, capitalization, dictionary check, pattern matching
- validate_place_name: relaxed rules for places
- filter_entities: filtering with confidence scores, curated fallback
- Confidence score calculation
- Performance: validation within 5ms per entity
"""
import time
import unittest
from unittest.mock import patch


class TestEntityValidatorPersonName(unittest.TestCase):
    """Tests for validate_person_name validation rules."""

    def setUp(self):
        # Patch NLTK to avoid network calls in tests
        with patch("backend.data.entity_validator._get_nltk_words") as mock_words:
            mock_words.return_value = {
                "abandoned", "accept", "ability", "the", "and", "or",
                "action", "adventure", "ancient", "beautiful", "captain",
            }
            from backend.data.entity_validator import EntityValidator
            self.validator = EntityValidator(strict_mode=True)
            # Manually set the dictionary words to our test set
            self.validator._dictionary_words = {
                "abandoned", "accept", "ability", "the", "and", "or",
                "action", "adventure", "ancient", "beautiful", "captain",
            }

    def test_valid_person_name_returns_true(self):
        """A proper person name should be valid."""
        is_valid, score, reason = self.validator.validate_person_name("Arjun")
        self.assertTrue(is_valid)
        self.assertGreater(score, 0.0)
        self.assertEqual(reason, "")

    def test_valid_multiword_name(self):
        """A multi-word proper name should be valid."""
        is_valid, score, reason = self.validator.validate_person_name("Vikram Singh")
        self.assertTrue(is_valid)
        self.assertGreater(score, 0.5)
        self.assertEqual(reason, "")

    def test_name_too_short_rejected(self):
        """Names shorter than 3 characters should be rejected."""
        is_valid, score, reason = self.validator.validate_person_name("Ab")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)
        self.assertIn("too short", reason)

    def test_name_exactly_min_length_accepted(self):
        """Names of exactly 3 characters should be accepted if otherwise valid."""
        is_valid, score, reason = self.validator.validate_person_name("Abi")
        self.assertTrue(is_valid)

    def test_name_too_long_rejected(self):
        """Names longer than 20 characters should be rejected."""
        long_name = "A" + "b" * 20  # 21 characters
        is_valid, score, reason = self.validator.validate_person_name(long_name)
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)
        self.assertIn("too long", reason)

    def test_name_exactly_max_length_accepted(self):
        """Names of exactly 20 characters should be accepted."""
        name = "Abcdefghijklmnopqrst"  # 20 chars
        self.assertEqual(len(name), 20)
        is_valid, score, reason = self.validator.validate_person_name(name)
        self.assertTrue(is_valid)

    def test_lowercase_first_letter_rejected(self):
        """Names not starting with uppercase should be rejected."""
        is_valid, score, reason = self.validator.validate_person_name("arjun")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)
        self.assertIn("uppercase", reason)

    def test_name_with_digits_rejected(self):
        """Names containing digits should be rejected for persons."""
        is_valid, score, reason = self.validator.validate_person_name("Arjun2")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)

    def test_name_with_special_chars_rejected(self):
        """Names with special characters should be rejected."""
        is_valid, score, reason = self.validator.validate_person_name("Arjun@Singh")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)

    def test_common_dictionary_word_rejected(self):
        """Common English dictionary words should be rejected as person names."""
        is_valid, score, reason = self.validator.validate_person_name("Abandoned")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)
        self.assertIn("dictionary word", reason)

    def test_common_word_accept_rejected(self):
        """'Accept' should be rejected as a person name."""
        is_valid, score, reason = self.validator.validate_person_name("Accept")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)

    def test_common_word_ability_rejected(self):
        """'Ability' should be rejected as a person name."""
        is_valid, score, reason = self.validator.validate_person_name("Ability")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)

    def test_empty_name_rejected(self):
        """Empty string should be rejected."""
        is_valid, score, reason = self.validator.validate_person_name("")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)
        self.assertIn("empty", reason)

    def test_whitespace_only_rejected(self):
        """Whitespace-only string should be rejected."""
        is_valid, score, reason = self.validator.validate_person_name("   ")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)

    def test_name_with_hyphen_accepted(self):
        """Hyphenated names should be accepted."""
        is_valid, score, reason = self.validator.validate_person_name("Mary-Jane")
        self.assertTrue(is_valid)

    def test_name_with_apostrophe_accepted(self):
        """Names with apostrophes should be accepted."""
        is_valid, score, reason = self.validator.validate_person_name("O'Brien")
        self.assertTrue(is_valid)


class TestEntityValidatorPlaceName(unittest.TestCase):
    """Tests for validate_place_name validation rules."""

    def setUp(self):
        from backend.data.entity_validator import EntityValidator
        self.validator = EntityValidator(strict_mode=True)
        self.validator._dictionary_words = {"the", "and", "or"}

    def test_valid_place_name(self):
        """A proper place name should be valid."""
        is_valid, score, reason = self.validator.validate_place_name("Mumbai")
        self.assertTrue(is_valid)
        self.assertGreater(score, 0.0)

    def test_place_name_too_short_rejected(self):
        """Place names shorter than 3 characters should be rejected."""
        is_valid, score, reason = self.validator.validate_place_name("LA")
        self.assertFalse(is_valid)
        self.assertEqual(score, 0.0)

    def test_place_name_too_long_rejected(self):
        """Place names longer than 20 characters should be rejected."""
        long_name = "A" * 21
        is_valid, score, reason = self.validator.validate_place_name(long_name)
        self.assertFalse(is_valid)

    def test_place_name_lowercase_rejected(self):
        """Place names not starting with uppercase should be rejected."""
        is_valid, score, reason = self.validator.validate_place_name("mumbai")
        self.assertFalse(is_valid)

    def test_multiword_place_name(self):
        """Multi-word place names should be valid."""
        is_valid, score, reason = self.validator.validate_place_name("New Delhi")
        self.assertTrue(is_valid)


class TestEntityValidatorConfidenceScoring(unittest.TestCase):
    """Tests for confidence score calculation."""

    def setUp(self):
        from backend.data.entity_validator import EntityValidator
        self.validator = EntityValidator(strict_mode=True)
        # Use a small dictionary for predictable scoring
        self.validator._dictionary_words = {
            "abandoned", "accept", "ability", "captain",
        }

    def test_confidence_score_in_range(self):
        """Confidence score should always be between 0.0 and 1.0."""
        names = ["Arjun", "Vikram Singh", "Abi", "Abcdefghijklmnopqrst"]
        for name in names:
            is_valid, score, _ = self.validator.validate_person_name(name)
            if is_valid:
                self.assertGreaterEqual(score, 0.0, f"Score for '{name}' below 0")
                self.assertLessEqual(score, 1.0, f"Score for '{name}' above 1")

    def test_multiword_name_higher_score_than_single(self):
        """Multi-word names should score higher than single-word names."""
        _, single_score, _ = self.validator.validate_person_name("Arjun")
        _, multi_score, _ = self.validator.validate_person_name("Arjun Singh")
        self.assertGreater(multi_score, single_score)

    def test_invalid_name_has_zero_score(self):
        """Invalid names should have a confidence score of 0.0."""
        _, score, _ = self.validator.validate_person_name("ab")  # too short
        self.assertEqual(score, 0.0)

    def test_ideal_length_name_gets_length_bonus(self):
        """Names in the ideal length range (4-15) should get a length bonus."""
        _, short_score, _ = self.validator.validate_person_name("Abi")  # 3 chars
        _, ideal_score, _ = self.validator.validate_person_name("Arjun")  # 5 chars
        self.assertGreaterEqual(ideal_score, short_score)

    def test_title_case_name_gets_capitalization_bonus(self):
        """Properly title-cased names should get a capitalization bonus."""
        _, score_title, _ = self.validator.validate_person_name("Vikram Singh")
        _, score_mixed, _ = self.validator.validate_person_name("Vikram singh")
        # Title case should score higher or equal
        self.assertGreaterEqual(score_title, score_mixed)


class TestEntityValidatorFilterEntities(unittest.TestCase):
    """Tests for filter_entities method."""

    def setUp(self):
        from backend.data.entity_validator import EntityValidator
        self.validator = EntityValidator(strict_mode=True)
        self.validator._dictionary_words = {
            "abandoned", "accept", "ability", "the", "and",
        }

    def test_filter_returns_valid_entities_with_scores(self):
        """filter_entities should return valid entities with confidence scores."""
        entities = ["Arjun", "Vikram", "Abandoned", "ab"]
        result = self.validator.filter_entities(entities, "person")
        names = [name for name, _ in result]
        self.assertIn("Arjun", names)
        self.assertIn("Vikram", names)
        self.assertNotIn("Abandoned", names)
        self.assertNotIn("ab", names)

    def test_filter_returns_scores_as_floats(self):
        """filter_entities should return float confidence scores."""
        entities = ["Arjun", "Vikram Singh"]
        result = self.validator.filter_entities(entities, "person")
        for name, score in result:
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_filter_sorted_by_score_descending(self):
        """filter_entities should return results sorted by score descending."""
        entities = ["Arjun", "Vikram Singh", "Abi"]
        result = self.validator.filter_entities(entities, "person")
        scores = [score for _, score in result]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_filter_all_rejected_falls_back_to_curated(self):
        """When all entities are rejected, should fall back to curated CHARACTERS list."""
        from backend.data.curated_lists import CHARACTERS
        # All invalid entities
        entities = ["ab", "cd", "Abandoned", "Accept"]
        result = self.validator.filter_entities(entities, "person")
        self.assertGreater(len(result), 0)
        names = [name for name, _ in result]
        # All fallback names should be from CHARACTERS
        for name in names:
            self.assertIn(name, CHARACTERS)

    def test_filter_empty_list_falls_back_to_curated(self):
        """Empty entity list should fall back to curated CHARACTERS list."""
        from backend.data.curated_lists import CHARACTERS
        result = self.validator.filter_entities([], "person")
        self.assertGreater(len(result), 0)
        names = [name for name, _ in result]
        for name in names:
            self.assertIn(name, CHARACTERS)

    def test_filter_place_entities(self):
        """filter_entities should work for place entity type."""
        entities = ["Mumbai", "Delhi", "ab", "New York"]
        result = self.validator.filter_entities(entities, "place")
        names = [name for name, _ in result]
        self.assertIn("Mumbai", names)
        self.assertIn("Delhi", names)
        self.assertNotIn("ab", names)

    def test_filter_returns_tuple_pairs(self):
        """filter_entities should return list of (name, score) tuples."""
        entities = ["Arjun"]
        result = self.validator.filter_entities(entities, "person")
        self.assertEqual(len(result), 1)
        name, score = result[0]
        self.assertEqual(name, "Arjun")
        self.assertIsInstance(score, float)


class TestEntityValidatorPerformance(unittest.TestCase):
    """Tests for validation performance (Requirement 4.6: <5ms per entity)."""

    def setUp(self):
        from backend.data.entity_validator import EntityValidator
        self.validator = EntityValidator(strict_mode=True)

    def test_validation_completes_within_5ms(self):
        """Validation should complete within 5ms per entity (Requirement 4.6)."""
        test_names = [
            "Arjun", "Vikram Singh", "Abandoned", "ab", "Mary-Jane",
            "O'Brien", "Abcdefghijklmnopqrst", "Captain", "Priya",
        ]
        for name in test_names:
            start = time.perf_counter()
            self.validator.validate_person_name(name)
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.assertLess(
                elapsed_ms,
                5.0,
                f"Validation of '{name}' took {elapsed_ms:.2f}ms (>5ms limit)",
            )

    def test_filter_entities_performance(self):
        """filter_entities on 100 entities should complete within 500ms."""
        entities = [f"Name{i:03d}" for i in range(100)]
        start = time.perf_counter()
        self.validator.filter_entities(entities, "person")
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertLess(elapsed_ms, 500.0, f"filter_entities took {elapsed_ms:.2f}ms")


class TestEntityValidatorIdempotence(unittest.TestCase):
    """Tests for validation idempotence (Requirement 4.7)."""

    def setUp(self):
        from backend.data.entity_validator import EntityValidator
        self.validator = EntityValidator(strict_mode=True)

    def test_validate_person_name_idempotent(self):
        """Validating the same name twice should produce identical results."""
        test_names = [
            "Arjun", "Vikram Singh", "Abandoned", "ab", "Mary-Jane",
            "Accept", "Priya", "New Delhi",
        ]
        for name in test_names:
            result1 = self.validator.validate_person_name(name)
            result2 = self.validator.validate_person_name(name)
            self.assertEqual(
                result1,
                result2,
                f"Validation of '{name}' not idempotent: {result1} != {result2}",
            )

    def test_filter_entities_idempotent(self):
        """Filtering the same entity list twice should produce identical results."""
        entities = ["Arjun", "Vikram", "Abandoned", "ab", "Priya"]
        result1 = self.validator.filter_entities(entities, "person")
        result2 = self.validator.filter_entities(entities, "person")
        self.assertEqual(result1, result2)


class TestEntityValidatorStrictVsNonStrict(unittest.TestCase):
    """Tests for strict vs non-strict mode behavior."""

    def setUp(self):
        from backend.data.entity_validator import EntityValidator
        self.strict = EntityValidator(strict_mode=True)
        self.lenient = EntityValidator(strict_mode=False)
        # Use same dictionary for both
        test_dict = {"captain", "action", "adventure"}
        self.strict._dictionary_words = test_dict
        self.lenient._dictionary_words = test_dict

    def test_strict_rejects_single_dictionary_word(self):
        """Strict mode should reject single-word names that are dictionary words."""
        is_valid, _, _ = self.strict.validate_person_name("Captain")
        self.assertFalse(is_valid)

    def test_lenient_also_rejects_single_dictionary_word(self):
        """Non-strict mode should also reject single-word dictionary names."""
        is_valid, _, _ = self.lenient.validate_person_name("Captain")
        self.assertFalse(is_valid)

    def test_strict_rejects_all_dictionary_multiword(self):
        """Strict mode should reject multi-word names where all words are dictionary words."""
        is_valid, _, _ = self.strict.validate_person_name("Captain Action")
        self.assertFalse(is_valid)

    def test_lenient_accepts_all_dictionary_multiword(self):
        """Non-strict mode should accept multi-word names even if all words are dictionary words."""
        is_valid, _, _ = self.lenient.validate_person_name("Captain Action")
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
