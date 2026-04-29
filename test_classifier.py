#!/usr/bin/env python3
"""
Test script to verify entity classification is working correctly.
Tests the classify_entity function with various test cases.
"""

import sys
sys.path.insert(0, '/Users/manikantapotla/Desktop/SCRIPTY/backend')

from dataset_processor import classify_entity, EntityClassifier

# Test cases
test_cases = {
    # NOISE - should return "noise"
    "noise": [
        ("Thou", "noise"),  # Archaic pronoun
        ("Herein", "noise"),  # Archaic term
        ("Behold", "noise"),  # Archaic verb
        ("Accompanied", "noise"),  # Common verb
        ("According", "noise"),  # Common verb
        ("Advance", "noise"),  # Common verb
        ("Ab", "noise"),  # Too short (< 3 chars)
        ("A", "noise"),  # Too short
        ("An", "noise"),  # Too short
    ],
    
    # PLACE - should return "place"
    "place": [
        ("Bengal", "place"),  # Known place
        ("Kasi", "place"),  # Known place
        ("Hastinapura", "place"),  # Known place (has "pur" suffix)
        ("Indraprastha", "place"),  # Has "tha" place-like suffix
        ("Mathura", "place"),  # Known place
        ("Varanasi", "place"),  # Known place (alternative name for Kasi)
    ],
    
    # CONCEPT - should return "concept"
    "concept": [
        ("Dharma", "concept"),  # Known concept
        ("Karma", "concept"),  # Known concept
        ("Atma", "concept"),  # Known concept (ends with "atma")
        ("Vedas", "concept"),  # Known concept
        ("Moksha", "concept"),  # Known concept
        ("Yoga", "concept"),  # Known concept (ends with "yoga")
    ],
    
    # PERSON (default fallback)
    "person": [
        ("Ahmad", "person"),  # Regular name
        ("Ravi", "person"),  # Regular Indian name
        ("Ashok", "person"),  # Regular Indian name
        ("Priya", "person"),  # Regular Indian name
        ("Rajesh", "person"),  # Regular Indian name
    ],
    
    # MYTHOLOGICAL - should be filtered as "noise"
    "mythological": [
        ("Indra", "noise"),  # God - should be filtered
        ("Agni", "noise"),  # God - should be filtered
        ("Krishna", "noise"),  # God - should be filtered
        ("Vishnu", "noise"),  # God - should be filtered
        ("Rama", "noise"),  # Epic hero - should be filtered
        ("Arjuna", "noise"),  # Epic hero - should be filtered
        ("Garuda", "noise"),  # Mythological creature - should be filtered
        ("Hanuman", "noise"),  # Mythological figure - should be filtered
    ],
}

def run_tests():
    """Run all test cases and report results."""
    print("=" * 70)
    print("ENTITY CLASSIFIER TEST SUITE")
    print("=" * 70)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category, cases in test_cases.items():
        print(f"\n✓ Testing {category.upper()}:")
        print("-" * 70)
        
        for word, expected in cases:
            result = classify_entity(word)
            total_tests += 1
            
            if result == expected:
                passed_tests += 1
                print(f"  ✓ {word:20} -> {result:10} (expected: {expected})")
            else:
                failed_tests += 1
                print(f"  ✗ {word:20} -> {result:10} (expected: {expected}) [FAILED]")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests:   {total_tests}")
    print(f"Passed:        {passed_tests}")
    print(f"Failed:        {failed_tests}")
    print(f"Success Rate:  {(passed_tests/total_tests)*100:.1f}%")
    print("=" * 70)
    
    if failed_tests == 0:
        print("✓ ALL TESTS PASSED!")
    else:
        print(f"✗ {failed_tests} TEST(S) FAILED")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
