"""64-story quality benchmark — measures dialogue, pronouns, artifacts, vocab, repetition."""

import asyncio
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.v2.engine import StoryEngineV2
from backend.v2.types import GenerationRequest, StoryMode

# ── 8 patterns × 8 variations ──────────────────────────────────────────

PATTERNS = {
    "Dialogue": {"location": "Hyderabad", "year": 1750, "genre": "historical", "theme": "negotiation and betrayal",
        "chars": [
            {"name": "Maya", "role": "negotiator", "traits": ["articulate", "cunning"], "goals": ["secure the alliance"]},
            {"name": "Arjun", "role": "ambassador", "traits": ["diplomatic", "suspicious"], "goals": ["protect the treaty"]},
        ]},
    "Romance": {"location": "Goa", "year": 1620, "genre": "romance", "theme": "forbidden love across divides",
        "chars": [
            {"name": "Lena", "role": "traveler", "traits": ["passionate", "reckless"], "goals": ["follow her heart"]},
            {"name": "Ravi", "role": "local", "traits": ["cautious", "devoted"], "goals": ["protect his family"]},
        ]},
    "Mystery": {"location": "Calcutta", "year": 1890, "genre": "mystery", "theme": "disappearance in the fog",
        "chars": [
            {"name": "Priya", "role": "detective", "traits": ["observant", "persistent"], "goals": ["find the truth"]},
            {"name": "Vikram", "role": "suspect", "traits": ["secretive", "nervous"], "goals": ["hide his involvement"]},
        ]},
    "Action": {"location": "Delhi", "year": 1526, "genre": "action", "theme": "race against time",
        "chars": [
            {"name": "Kiran", "role": "warrior", "traits": ["brave", "impulsive"], "goals": ["defend the fortress"]},
            {"name": "Zara", "role": "spy", "traits": ["quick", "resourceful"], "goals": ["sabotage the siege"]},
        ]},
    "Tragedy": {"location": "Lucknow", "year": 1857, "genre": "tragedy", "theme": "last stand and sacrifice",
        "chars": [
            {"name": "Farid", "role": "soldier", "traits": ["loyal", "melancholic"], "goals": ["protect his men"]},
            {"name": "Amara", "role": "healer", "traits": ["compassionate", "fatalistic"], "goals": ["save who she can"]},
        ]},
    "Sci-Fi": {"location": "Neo Mumbai", "year": 2150, "genre": "sci-fi", "theme": "first contact protocol",
        "chars": [
            {"name": "Nova", "role": "commander", "traits": ["analytical", "decisive"], "goals": ["establish communication"]},
            {"name": "Kael", "role": "xenologist", "traits": ["curious", "cautious"], "goals": ["prevent misunderstanding"]},
        ]},
    "Descriptive": {"location": "Varanasi", "year": 1880, "genre": "historical", "theme": "the eternal city",
        "chars": [
            {"name": "Sita", "role": "pilgrim", "traits": ["contemplative", "spiritual"], "goals": ["find inner peace"]},
            {"name": "Deven", "role": "guide", "traits": ["patient", "knowledgeable"], "goals": ["share the city's stories"]},
        ]},
    "Introspection": {"location": "Shimla", "year": 1942, "genre": "historical", "theme": "a moment of decision",
        "chars": [
            {"name": "Ishaan", "role": "thinker", "traits": ["introspective", "uncertain"], "goals": ["choose his path"]},
            {"name": "Meera", "role": "confidante", "traits": ["wise", "gentle"], "goals": ["guide without controlling"]},
        ]},
}

VARIATIONS = [
    {"mood": "default"},
    {"mood": "urgent"},
    {"mood": "reflective"},
    {"mood": "tense"},
    {"mood": "hopeful"},
    {"mood": "somber"},
    {"mood": "mysterious"},
    {"mood": "dramatic"},
]

_FEMALE_NAMES = {"Lena", "Priya", "Zara", "Amara", "Nova", "Sita", "Meera"}
_MALE_NAMES = {"Arjun", "Ravi", "Vikram", "Kiran", "Farid", "Kael", "Deven", "Ishaan"}

def measure_quality(text: str, characters: list[dict]) -> dict:
    """Measure quality metrics for generated story text."""
    words = text.split()
    word_count = len(words)

    # Dialogue
    lq = text.count('\u201c')
    rq = text.count('\u201d')
    quote_pairs = min(lq, rq)
    dialogue_words = 0
    in_quote = False
    for w in words:
        if '\u201c' in w or '\u201d' in w:
            in_quote = not in_quote
        if in_quote:
            dialogue_words += 1
    dialogue_density = dialogue_words / max(word_count, 1)

    # Goal leakage — check all character goals
    goal_leaks = 0
    for c in characters:
        for g in c.get("goals", []):
            if g.lower() in text.lower():
                goal_leaks += 1

    # Double punctuation
    double_punc = len(re.findall(r'[.,;:!?]{2,}', text))
    # Exclude ellipsis
    ellipsis = text.count('...')
    double_punc = max(0, double_punc - ellipsis)

    # Pronoun agreement for female character
    pronoun_issues = 0
    for c in characters:
        name = c["name"]
        if name in _FEMALE_NAMES:
            # Count "he"/"his" in proximity to female name (< 3 words away)
            name_positions = [m.start() for m in re.finditer(rf'\b{name}\b', text)]
            for pos in name_positions:
                window = text[max(0,pos-50):pos+50]
                for m in re.finditer(r'\b(he|his|him)\b', window.lower()):
                    pronoun_issues += 1
        elif name in _MALE_NAMES:
            name_positions = [m.start() for m in re.finditer(rf'\b{name}\b', text)]
            for pos in name_positions:
                window = text[max(0,pos-50):pos+50]
                for m in re.finditer(r'\b(she|her)\b', window.lower()):
                    pronoun_issues += 1

    # Memory artifacts — stray single-letter words (excl a/A/I), list repr
    memory_artifacts = 0
    single_letters = re.findall(r"\b[b-hj-zB-HJ-Z]\b", text)
    memory_artifacts += len(single_letters)
    list_repr = len(re.findall(r"\['.*?'\]", text))
    memory_artifacts += list_repr
    memory_markers = sum(text.lower().count(p) for p in [
        " stirred in ", " flickered through ", " the memory of ",
        " a ghost that would not stay buried",
    ])
    memory_artifacts += memory_markers

    # Vocabulary diversity
    unique_words = len(set(w.lower().strip(".,;:\"'!?()[]") for w in words))
    vocab_diversity = unique_words / max(word_count, 1)

    # Bigram repetition
    bigrams = []
    for i in range(len(words) - 1):
        bg = (words[i].lower(), words[i+1].lower())
        bigrams.append(bg)
    total_bigrams = len(bigrams)
    unique_bigrams = len(set(bigrams))
    bigram_rep = 1 - (unique_bigrams / max(total_bigrams, 1))

    return {
        "word_count": word_count,
        "quote_pairs": quote_pairs,
        "dialogue_density": round(dialogue_density, 4),
        "goal_leaks": goal_leaks,
        "double_punctuation": double_punc,
        "pronoun_issues": pronoun_issues,
        "memory_artifacts": memory_artifacts,
        "unique_words": unique_words,
        "vocab_diversity": round(vocab_diversity, 4),
        "bigram_rep": round(bigram_rep, 4),
    }


async def run_benchmark() -> list[dict]:
    eng = StoryEngineV2()
    results = []

    for pname, pdata in PATTERNS.items():
        for vi, var in enumerate(VARIATIONS):
            req = GenerationRequest(
                location=pdata["location"],
                year=pdata["year"],
                location_type="urban",
                story_mode=StoryMode.SHORT,
                genre=pdata["genre"],
                theme=f"{pdata['theme']}, {var['mood']} mood",
                characters=pdata["chars"],
            )
            start = time.time()
            try:
                result = await eng.generate(req)
                elapsed = time.time() - start
                quality = measure_quality(result.story_text, pdata["chars"])
                quality["pattern"] = pname
                quality["variation"] = var["mood"]
                quality["success"] = True
                quality["time"] = round(elapsed, 3)
                quality["story_text"] = result.story_text[:500]
                results.append(quality)
                print(f"  ✓ {pname:15s} [{var['mood']:12s}] {result.word_count:4d}w {quality['quote_pairs']}q "
                      f"gl={quality['goal_leaks']} pp={quality['pronoun_issues']} ma={quality['memory_artifacts']}")
            except Exception as e:
                elapsed = time.time() - start
                results.append({
                    "pattern": pname, "variation": var["mood"], "success": False,
                    "word_count": 0, "error": str(e), "time": round(elapsed, 3),
                })
                print(f"  ✗ {pname:15s} [{var['mood']:12s}] FAILED: {str(e)[:60]}")

    return results


def generate_report(results: list[dict]):
    """Generate markdown report."""
    lines = ["# 64-Story Quality Benchmark Report\n",
             f"Generated {len(results)} stories, {sum(1 for r in results if r.get('success'))} succeeded, "
             f"{sum(1 for r in results if not r.get('success'))} failed\n"]

    # Per-pattern summary
    from collections import defaultdict
    by_pattern = defaultdict(list)
    for r in results:
        if r.get("success"):
            by_pattern[r["pattern"]].append(r)

    lines.append("## Per-Pattern Summary\n")
    lines.append("| Pattern | Avg Words | Avg Vocab | Quote Pairs | Dialogue Dens | Goal Leaks | Pronoun Iss | Mem Artifacts | Bigram Rep |\n"
                 "|---------|-----------|-----------|-------------|---------------|------------|-------------|---------------|------------|")
    for pname in sorted(by_pattern.keys(), key=lambda p: -statistics.mean([r["word_count"] for r in by_pattern[p]])):
        p = by_pattern[pname]
        avg_w = statistics.mean([r["word_count"] for r in p])
        avg_v = statistics.mean([r["unique_words"] for r in p])
        avg_q = statistics.mean([r["quote_pairs"] for r in p])
        avg_dd = statistics.mean([r["dialogue_density"] for r in p])
        avg_gl = statistics.mean([r["goal_leaks"] for r in p])
        avg_pp = statistics.mean([r["pronoun_issues"] for r in p])
        avg_ma = statistics.mean([r["memory_artifacts"] for r in p])
        avg_br = statistics.mean([r["bigram_rep"] for r in p])
        lines.append(f"| {pname:12s} | {avg_w:7.0f} | {avg_v:7.0f} | {avg_q:9.1f} | {avg_dd:9.3f} | {avg_gl:8.1f} | {avg_pp:9.1f} | {avg_ma:10.1f} | {avg_br:8.3f} |")

    # Overall
    all_success = [r for r in results if r.get("success")]
    lines.append("\n## Overall\n")
    lines.append(f"| Metric | Value |\n|--------|-------|")
    lines.append(f"| Avg words | {statistics.mean([r['word_count'] for r in all_success]):.0f} |")
    lines.append(f"| Avg unique vocab | {statistics.mean([r['unique_words'] for r in all_success]):.0f} |")
    lines.append(f"| Avg dialogue density | {statistics.mean([r['dialogue_density'] for r in all_success]):.4f} |")
    lines.append(f"| Avg goal leaks | {statistics.mean([r['goal_leaks'] for r in all_success]):.2f} |")
    lines.append(f"| Avg pronoun issues | {statistics.mean([r['pronoun_issues'] for r in all_success]):.2f} |")
    lines.append(f"| Avg memory artifacts | {statistics.mean([r['memory_artifacts'] for r in all_success]):.1f} |")
    lines.append(f"| Avg bigram repetition | {statistics.mean([r['bigram_rep'] for r in all_success]):.4f} |")

    # Comparison with previous baseline
    lines.append("\n## Comparison with Previous Benchmark (64-story, June 2026)\n")
    lines.append("| Metric | Before | After | Change |\n|--------|--------|-------|--------|")
    # Previous baseline (from reports/sixtyfour_story_analysis.md)
    prev = {
        "Dialogue": {"avg_words": 785.9, "vocab": 283},
        "Romance": {"avg_words": 657.0, "vocab": 235},
        "Mystery": {"avg_words": 787.9, "vocab": 300},
        "Action": {"avg_words": 601.4, "vocab": 217},
        "Tragedy": {"avg_words": 639.8, "vocab": 228},
        "Sci-Fi": {"avg_words": 573.9, "vocab": 206},
        "Descriptive": {"avg_words": 258.3, "vocab": 74},
        "Introspection": {"avg_words": 250.9, "vocab": 67},
    }
    for pname, pdata in sorted(prev.items()):
        curr = by_pattern.get(pname, [])
        if curr:
            curr_w = statistics.mean([r["word_count"] for r in curr])
            curr_v = statistics.mean([r["unique_words"] for r in curr])
            curr_q = statistics.mean([r["quote_pairs"] for r in curr])
            lines.append(f"| {pname:12s} words | {pdata['avg_words']:5.0f} | {curr_w:5.0f} | {curr_w-pdata['avg_words']:+5.0f} |")
            lines.append(f"| {pname:12s} vocab  | {pdata['vocab']:5d} | {curr_v:5.0f} | {curr_v-pdata['vocab']:+5.0f} |")
            lines.append(f"| {pname:12s} quotes | {'0 (ASCII)':>5s} | {curr_q:5.1f} | Unicode now |")

    lines.append("\n## Issues Found\n")
    # Collect issues
    issues = []
    for r in all_success:
        if r["pronoun_issues"] > 3:
            issues.append(f"- **{r['pattern']}/{r['variation']}**: {r['pronoun_issues']} pronoun issues")
        if r["goal_leaks"] > 0:
            issues.append(f"- **{r['pattern']}/{r['variation']}**: {r['goal_leaks']} goal leaks")
        if r["double_punctuation"] > 2:
            issues.append(f"- **{r['pattern']}/{r['variation']}**: {r['double_punctuation']} double punctuation")
        if r["memory_artifacts"] > 15:
            issues.append(f"- **{r['pattern']}/{r['variation']}**: {r['memory_artifacts']} memory artifacts")
        if r["bigram_rep"] > 0.5:
            issues.append(f"- **{r['pattern']}/{r['variation']}**: bigram rep {r['bigram_rep']:.3f}")
        if r["dialogue_density"] > 0.5:
            pass  # high dialogue density is good
    if issues:
        lines.extend(issues[:30])
        if len(issues) > 30:
            lines.append(f"- ... and {len(issues)-30} more issues")
    else:
        lines.append("(none critical)")

    return "\n".join(lines)


async def main():
    print("Running 64-story quality benchmark...\n")
    results = await run_benchmark()
    report = generate_report(results)

    out_path = Path(__file__).parent.parent.parent.parent / "reports" / "quality_benchmark_64.md"
    out_path.write_text(report)
    print(f"\nReport saved to {out_path}")

    # Save raw data
    data_path = Path(__file__).parent.parent.parent.parent / "reports" / "quality_benchmark_64.json"
    clean = [{k:v for k,v in r.items() if k != "story_text"} for r in results]
    data_path.write_text(json.dumps(clean, indent=2))
    print(f"Raw data saved to {data_path}")

    print("\n=== Summary ===")
    success = [r for r in results if r.get("success")]
    print(f"Success rate: {len(success)}/{len(results)}")
    if success:
        print(f"Avg words: {statistics.mean([r['word_count'] for r in success]):.0f}")
        print(f"Avg quote pairs: {statistics.mean([r['quote_pairs'] for r in success]):.1f}")
        print(f"Avg dialogue density: {statistics.mean([r['dialogue_density'] for r in success]):.4f}")
        print(f"Avg goal leaks: {statistics.mean([r['goal_leaks'] for r in success]):.2f}")
        print(f"Avg pronoun issues: {statistics.mean([r['pronoun_issues'] for r in success]):.2f}")
        print(f"Avg memory artifacts: {statistics.mean([r['memory_artifacts'] for r in success]):.1f}")
        print(f"Avg bigram rep: {statistics.mean([r['bigram_rep'] for r in success]):.4f}")

if __name__ == "__main__":
    asyncio.run(main())
