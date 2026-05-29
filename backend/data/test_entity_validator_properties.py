"""
Property-based tests for EntityValidator (Task 3.3)

Tests cover:
- Property 3: Entity validation idempotence
  Validates: Requirements 4.7
  For any entity name, applying validation twice SHALL produce identical
  results (same validity status, confidence score, and rejection reason
  if applicable).
"""
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st


class TestEntityValidationIdempotence(unittest.TestCase):
    """
    Property 3: Entity validation idempotence

    **Validates: Requirements 4.7**

    FOR ALL entity names, applying validation twice SHALL produce identical
    results (same validity status, confidence score, and rejection reason
    if applicable).
    """

    @given(
        entity_name=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters=" -'.",
            ),
            min_size=0,
            max_size=50,
        ),
        entity_type=st.sampled_from(["person", "place"]),
        strict_mode=st.booleans(),
    )
    @settings(max_examples=20)
    def test_validate_entity_idempotent(self, entity_name, entity_type, strict_mode):
        """
        **Validates: Requirements 4.7**

        Property: For any entity name and entity type, the sequence:
          1. validate(entity_name, entity_type) → (is_valid1, score1, reason1)
          2. validate(entity_name, entity_type) → (is_valid2, score2, reason2)

        Must satisfy: (is_valid1, score1, reason1) == (is_valid2, score2, reason2)
        """
        from backend.data.entity_validator import EntityValidator

        validator = EntityValidator(strict_mode=strict_mode)

        # First validation
        if entity_type == "person":
            result1 = validator.validate_person_name(entity_name)
        else:  # place
            result1 = validator.validate_place_name(entity_name)

        # Second validation (should be identical)
        if entity_type == "person":
            result2 = validator.validate_person_name(entity_name)
        else:  # place
            result2 = validator.validate_place_name(entity_name)

        # Assert idempotence: both results must be identical
        self.assertEqual(
            result1,
            result2,
            f"Validation of entity_name={entity_name!r} (type={entity_type}, "
            f"strict={strict_mode}) is not idempotent:\n"
            f"  First:  {result1}\n"
            f"  Second: {result2}",
        )

        # Unpack and verify each component separately for clarity
        is_valid1, score1, reason1 = result1
        is_valid2, score2, reason2 = result2

        self.assertEqual(
            is_valid1,
            is_valid2,
            f"Validity status differs for entity_name={entity_name!r}",
        )
        self.assertEqual(
            score1,
            score2,
            f"Confidence score differs for entity_name={entity_name!r}",
        )
        self.assertEqual(
            reason1,
            reason2,
            f"Rejection reason differs for entity_name={entity_name!r}",
        )

    @given(
        entities=st.lists(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"),
                    whitelist_characters=" -'.",
                ),
                min_size=0,
                max_size=30,
            ),
            min_size=0,
            max_size=20,
        ),
        entity_type=st.sampled_from(["person", "place"]),
        strict_mode=st.booleans(),
    )
    @settings(max_examples=20, deadline=None)
    def test_filter_entities_idempotent(self, entities, entity_type, strict_mode):
        """
        **Validates: Requirements 4.7**

        Property: For any list of entities, the sequence:
          1. filter_entities(entities, entity_type) → result1
          2. filter_entities(entities, entity_type) → result2

        Must satisfy: result1 == result2

        This tests that the filter_entities method is also idempotent.
        """
        from backend.data.entity_validator import EntityValidator

        validator = EntityValidator(strict_mode=strict_mode)

        # First filtering
        result1 = validator.filter_entities(entities, entity_type)

        # Second filtering (should be identical)
        result2 = validator.filter_entities(entities, entity_type)

        # Assert idempotence: both results must be identical
        self.assertEqual(
            result1,
            result2,
            f"filter_entities for entities={entities!r} (type={entity_type}, "
            f"strict={strict_mode}) is not idempotent:\n"
            f"  First:  {result1}\n"
            f"  Second: {result2}",
        )

        # Verify that the lists have the same length
        self.assertEqual(
            len(result1),
            len(result2),
            f"Filtered entity list length differs for entities={entities!r}",
        )

        # Verify each (name, score) tuple is identical
        for i, ((name1, score1), (name2, score2)) in enumerate(zip(result1, result2)):
            self.assertEqual(
                name1,
                name2,
                f"Entity name at index {i} differs: {name1!r} vs {name2!r}",
            )
            self.assertEqual(
                score1,
                score2,
                f"Confidence score at index {i} differs for entity {name1!r}: "
                f"{score1} vs {score2}",
            )


if __name__ == "__main__":
    unittest.main()

