"""Dynamic audit: measure token efficiency, character differentiation, coherence."""

import asyncio
import os
import statistics


def _make_req(characters=None):
    from backend.v2.types import GenerationRequest, StoryMode
    return GenerationRequest(
        location="Hyderabad",
        year=1920,
        story_mode=StoryMode.SHORT,
        chapter_count=1,
        genre="Historical Fiction",
        theme="resilience",
        characters=characters or [],
        location_type="urban",
        style_instructions="",
    )


async def measure_token_efficiency():
    """Ratio of unique tokens to total tokens. Higher = more diverse."""
    from backend.v2.engine import StoryEngineV2
    
    engine = StoryEngineV2(enable_hwse=False)
    request = _make_req()
    result = await engine.generate(request)

    words = result.story_text.split()
    total = len(words)
    unique = len(set(w.lower().strip(".,!?;:\"'") for w in words))

    print(f"Token efficiency:")
    print(f"  Total words: {total}")
    print(f"  Unique words: {unique}")
    print(f"  Type-token ratio: {unique/total:.3f}")
    print(f"  Unique bigrams: ", end="")
    bigrams = set()
    for i in range(len(words) - 1):
        bigrams.add(f"{words[i].lower()} {words[i+1].lower()}")
    print(f"{len(bigrams)} / {max(total-1, 1)} = {len(bigrams)/max(total-1, 1):.3f}")
    print(f"  Shared bigram ratio (1 - unique/total): {1 - len(bigrams)/max(total-1, 1):.4f}")
    print(f"  Sentence count: {len(result.story_text.split(chr(46)))}")
    print(f"  Avg sentence length: {total / max(len(result.story_text.split(chr(46))), 1):.1f} words")
    print()


async def measure_character_differentiation():
    """Generate stories with different character profiles and compare output."""
    from backend.v2.engine import StoryEngineV2
    import collections

    profiles = [
        ("Brave leader", [{"name": "Arjun", "role": "hero", "traits": ["brave", "loyal", "impulsive"]}, {"name": "Nadia", "role": "ally", "traits": ["cautious", "kind"]}]),
        ("Cunning scholar", [{"name": "Kavya", "role": "sage", "traits": ["cunning", "learned", "patient"]}, {"name": "Rohan", "role": "ally", "traits": ["curious", "hopeful"]}]),
        ("Rude brat", [{"name": "Vikram", "role": "trickster", "traits": ["rude", "brash", "arrogant"]}, {"name": "Zara", "role": "ally", "traits": ["patient", "wise"]}]),
        ("Melancholic poet", [{"name": "Meera", "role": "bystander", "traits": ["melancholic", "gentle", "mysterious"]}, {"name": "Ishaan", "role": "ally", "traits": ["kind", "gentle"]}]),
    ]

    results = {}
    for label, chars in profiles:
        engine = StoryEngineV2(enable_hwse=False)
        request = _make_req(chars)
        result = await engine.generate(request)
        results[label] = result.story_text
        print(f"--- {label} ---")
        # Count dialogue occurrences (either at line start or mid-line)
        dialogue_count = result.story_text.count("\u201c")
        words = result.story_text.split()
        word_count = len(words)
        unique_words = len(set(w.lower().strip(".,!?;:\"'") for w in words))
        print(f"  Words: {word_count}, Unique: {unique_words}, TTR: {unique_words/word_count:.3f}")
        print(f"  Dialogue lines: {dialogue_count}")
        print()

    # Cross-character overlap: count shared trigrams
    print("--- Cross-character overlap (trigram Jaccard similarity) ---")
    all_texts = list(results.values())
    all_labels = list(results.keys())
    for i in range(len(all_texts)):
        for j in range(i+1, len(all_texts)):
            trigrams_i = set()
            trigrams_j = set()
            words_i = all_texts[i].lower().split()
            words_j = all_texts[j].lower().split()
            for k in range(len(words_i) - 2):
                trigrams_i.add(" ".join(words_i[k:k+3]))
            for k in range(len(words_j) - 2):
                trigrams_j.add(" ".join(words_j[k:k+3]))
            intersection = len(trigrams_i & trigrams_j)
            union = len(trigrams_i | trigrams_j)
            jaccard = intersection / max(union, 1)
            print(f"  {all_labels[i]} vs {all_labels[j]}: J={jaccard:.3f} ({intersection}/{union})")
    print()


async def measure_memory_density():
    """How many distinct past events are referenced per scene."""
    from backend.v2.engine import StoryEngineV2

    engine = StoryEngineV2(enable_hwse=False)
    request = _make_req([{"name": "Arjun", "role": "protagonist", "traits": ["brave"]}])
    result = await engine.generate(request)
    
    # Count memory-related keywords in output
    text_lower = result.story_text.lower()
    memory_markers = [
        "remember", "forgot", "memory", "recall", "before", "past",
        "remembered", "forgotten", "recalled", "reminded", "ever since",
        "used to", "had never", "had always", "could not forget",
    ]
    memory_count = sum(text_lower.count(m) for m in memory_markers)
    
    print(f"Memory density:")
    print(f"  Total words: {len(result.story_text.split())}")
    print(f"  Memory-marker occurrences: {memory_count}")
    print(f"  Memory density: {memory_count / max(len(result.story_text.split()), 1) * 1000:.2f} per 1000 words")
    
    # Count callback phrases
    callback_phrases = ["dark memory", "warm memory", "bitter memory", "regretful memory", "memory surfaced"]
    callback_count = sum(text_lower.count(p) for p in callback_phrases)
    print(f"  Callback template hits: {callback_count}")
    print()


async def measure_structural_diversity():
    """Compare multiple stories for structural repetition."""
    from backend.v2.engine import StoryEngineV2

    stories = []
    prompts = [
        ("Hyderabad", 1920, "Historical Fiction", "resilience"),
        ("Mumbai", 2020, "Mystery", "betrayal"),
        ("Delhi", 1857, "Adventure", "revolution"),
        ("Chennai", 1980, "Romance", "separation"),
    ]
    
    for loc, year, genre, theme in prompts:
        engine = StoryEngineV2(enable_hwse=False)
        request = _make_req([{"name": "Arjun", "role": "protagonist", "traits": ["brave"]}])
        request.location = loc
        request.year = year
        request.genre = genre
        request.theme = theme
        result = await engine.generate(request)
        stories.append((loc, year, genre, result.story_text))
    
    # Count shared opening structures
    openings = []
    for loc, year, genre, text in stories:
        first_para = text.split("\n\n")[0] if "\n\n" in text else text[:200]
        openings.append(first_para)
    
    print(f"Structural diversity ({len(stories)} stories):")
    for i, (loc, year, genre, text) in enumerate(stories):
        words = text.split()
        print(f"  {i+1}. {loc}, {year} ({genre}): {len(words)} words, opens with: {words[:10]}...")

    # Count shared sentence start words
    from collections import Counter
    all_starts = []
    for _, _, _, text in stories:
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        for s in sentences:
            words = s.strip().split()
            if words:
                all_starts.append(words[0].lower().strip(chr(8220)))

    start_counts = Counter(all_starts)
    top_starts = start_counts.most_common(10)
    total = sum(start_counts.values())
    print(f"\n  Top sentence-start words ({total} sentences):")
    for word, count in top_starts:
        print(f"    \"{word}\": {count} ({count/total*100:.1f}%)")
    print()


async def main():
    print("=" * 60)
    print("DYNAMIC AUDIT: v2 Engine Runtime Measurements")
    print("=" * 60)
    print()
    await measure_token_efficiency()
    await measure_character_differentiation()
    await measure_memory_density()
    await measure_structural_diversity()
    print("=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
