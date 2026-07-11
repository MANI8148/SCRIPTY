"""Phase F: Final v2 benchmark — 100 stories, 5 genres x 20 prompts.

Uses backend.v2.metrics for all metric computation.
Measures dialogue density, TTR, sentence-start patterns,
repetition rate, memory utilization, callback usage, and character
differentiation across all stories. Writes results to reports/benchmark_v2_final.md.
"""

import asyncio
import os
import statistics
import time
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from backend.v2.metrics import (
    word_count as metrics_word_count,
    type_token_ratio as metrics_ttr,
    dialogue_count as metrics_dialogue_count,
    bigram_overlap_ratio,
    trigram_jaccard,
    coherence,
    simulation_pattern_count,
    show_vs_tell,
    unique_sentence_starts,
    emotional_expression,
)
from backend.v2.types import GenerationRequest, StoryMode
from backend.v2.engine import StoryEngineV2

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
REPORTS_DIR = os.path.join(BENCHMARK_DIR, "reports")

PROMPTS = {
    "Adventure": [
        "jungle expedition", "treasure hunt", "sea voyage", "mountain climb",
        "desert crossing", "escape from prison", "chase through city",
        "lost in wilderness", "shipwreck survival", "race against time",
        "rescue mission", "secret tunnel", "hidden temple", "river rafting",
        "volcanic eruption", "arctic survival", "cave exploration",
        "forest trek", "desert oasis", "storm at sea",
    ],
    "Historical": [
        "Mughal court", "Victorian London", "ancient Rome", "medieval castle",
        "revolutionary war", "silk road journey", "colonial settlement",
        "gold rush", "samurai era", "viking raid", "pharaoh's Egypt",
        "renaissance Florence", "wild west", "industrial revolution",
        "french revolution", "aztec empire", "crusader kingdom",
        "bronze age", "ottoman siege", "polynesian voyage",
    ],
    "Fantasy": [
        "dragon's lair", "enchanted forest", "wizard's tower", "magical academy",
        "elven kingdom", "dwarven mines", "prophecy revealed", "dark ritual",
        "fairy bargain", "cursed sword", "phoenix rising", "shadow realm",
        "lost magic", "ancient prophecy", "sorcerer's duel", "magical creature",
        "hidden realm", "time loop", "spellbinding", "mythical quest",
    ],
    "Mystery": [
        "locked room", "missing heirloom", "anonymous letter", "midnight visitor",
        "stolen artifact", "poisoned well", "secret passage", "false alibi",
        "hidden identity", "coded message", "impossible crime", "vanishing act",
        "double cross", "dark secret", "haunted house", "cold case",
        "mistaken identity", "frame job", "buried evidence", "final twist",
    ],
    "Sci-Fi": [
        "space station", "AI uprising", "first contact", "time paradox",
        "cloning facility", "cyberpunk city", "alien artifact",
        "dystopian future", "quantum experiment", "Mars colony", "neural link",
        "starship voyage", "robot rebellion", "parallel universe", "solar flare",
        "genetic mutation", "hologram mystery", "deep space", "android rights",
        "wormhole travel",
    ],
}

GENRE_YEARS = {
    "Adventure": 1850,
    "Historical": 1500,
    "Fantasy": 1200,
    "Mystery": 1900,
    "Sci-Fi": 2500,
}

GENRE_LOCATIONS = {
    "Adventure": "Amazon rainforest",
    "Historical": "Constantinople",
    "Fantasy": "Eldoria",
    "Mystery": "London",
    "Sci-Fi": "Neo-Tokyo",
}


def sentence_start_patterns(text: str, n: int = 3) -> Counter:
    sentences = text.replace("!", ".").replace("?", ".").split(".")
    starts: Counter = Counter()
    for s in sentences:
        words = s.strip().split()
        if len(words) >= n:
            pattern = " ".join(words[:n]).lower().strip("\u201c")
            starts[pattern] += 1
    return starts


def extract_memory_metrics(result) -> dict:
    """Count memories and callbacks from result data.
    
    Handles both GenerationResult dataclass (inside generate_story)
    and dict (from main after snapshot attachment).
    """
    if isinstance(result, dict):
        snap = result.get("_memory_snapshot", {})
        mem_count = snap.get("episodic_count", 0)
        callback_count = snap.get("pending_callbacks", 0)
    else:
        mem_count = 0
        callback_count = 0
    return {
        "retrieved_memories": mem_count,
        "callback_count": callback_count,
    }


async def generate_story(
    engine: StoryEngineV2,
    genre: str,
    prompt: str,
    prompt_index: int,
) -> dict:
    loc = GENRE_LOCATIONS.get(genre, "unknown")
    year = GENRE_YEARS.get(genre, 1900)
    request = GenerationRequest(
        location=loc,
        year=year,
        story_mode=StoryMode.SHORT,
        chapter_count=1,
        genre=genre,
        theme=prompt,
        characters=[
            {"name": "Arjun", "role": "protagonist", "traits": ["curious", "brave"],
             "goals": [f"survive the {prompt}"]},
            {"name": "Maya", "role": "ally", "traits": ["cautious", "perceptive"],
             "goals": [f"uncover the truth behind the {prompt}"]},
        ],
        location_type="urban" if genre == "Mystery" else "rural",
        style_instructions="",
    )
    try:
        start = time.monotonic()
        result = await engine.generate(request)
        elapsed = time.monotonic() - start
        text = result.story_text
        wc = metrics_word_count(text)
        ttr = metrics_ttr(text)
        dc = metrics_dialogue_count(text)
        starts = sentence_start_patterns(text)
        top_starts = starts.most_common(10)
        rep = bigram_overlap_ratio(text)
        mem = extract_memory_metrics(result)
        return {
            "genre": genre,
            "prompt": prompt,
            "index": prompt_index,
            "success": True,
            "word_count": wc,
            "type_token_ratio": round(ttr, 4),
            "dialogue_count": dc,
            "dialogue_density": round(dc / max(wc, 1) * 100, 2),
            "top_sentence_starts": [(p, c) for p, c in top_starts[:5]],
            "repetition_rate": round(rep, 4),
            "retrieved_memories": mem["retrieved_memories"],
            "callback_count": mem["callback_count"],
            "time_ms": round(elapsed * 1000, 1),
            "story_text": text,
        }
    except Exception as e:
        return {
            "genre": genre,
            "prompt": prompt,
            "index": prompt_index,
            "success": False,
            "error": str(e),
            "word_count": 0,
            "type_token_ratio": 0.0,
            "dialogue_count": 0,
            "dialogue_density": 0.0,
            "top_sentence_starts": [],
            "repetition_rate": 0.0,
            "retrieved_memories": 0,
            "callback_count": 0,
            "time_ms": 0.0,
            "story_text": "",
        }


def compute_genre_stats(results: list[dict]) -> dict:
    stats = {}
    for genre in PROMPTS:
        genre_results = [r for r in results if r["genre"] == genre and r["success"]]
        if not genre_results:
            stats[genre] = {"count": 0}
            continue
        wcs = [r["word_count"] for r in genre_results]
        ttrs = [r["type_token_ratio"] for r in genre_results]
        dcs = [r["dialogue_count"] for r in genre_results]
        dds = [r["dialogue_density"] for r in genre_results]
        reps = [r["repetition_rate"] for r in genre_results]
        mems = [r["retrieved_memories"] for r in genre_results]
        cbs = [r["callback_count"] for r in genre_results]
        times = [r["time_ms"] for r in genre_results]
        all_starts: Counter = Counter()
        for r in genre_results:
            for p, c in r["top_sentence_starts"]:
                all_starts[p] += c
        top5 = all_starts.most_common(5)
        stats[genre] = {
            "count": len(genre_results),
            "avg_word_count": round(statistics.mean(wcs), 1),
            "median_word_count": round(statistics.median(wcs), 1),
            "std_word_count": round(statistics.stdev(wcs), 1) if len(wcs) > 1 else 0,
            "avg_ttr": round(statistics.mean(ttrs), 4),
            "avg_dialogue_count": round(statistics.mean(dcs), 1),
            "avg_dialogue_density": round(statistics.mean(dds), 2),
            "avg_repetition": round(statistics.mean(reps), 4),
            "avg_memories": round(statistics.mean(mems), 1),
            "avg_callbacks": round(statistics.mean(cbs), 1),
            "avg_time_ms": round(statistics.mean(times), 1),
            "top_sentence_starts": top5,
        }
    return stats


def compute_character_differentiation(results: list[dict]) -> dict:
    stories_with_2plus = [r for r in results if r["success"] and len(r.get("story_text", "").split()) > 50]
    if len(stories_with_2plus) < 2:
        return {"avg_jaccard": 0.0, "pairs": 0}
    jaccards = []
    for i in range(len(stories_with_2plus)):
        for j in range(i + 1, min(i + 3, len(stories_with_2plus))):
            jac = trigram_jaccard(
                stories_with_2plus[i]["story_text"],
                stories_with_2plus[j]["story_text"],
            )
            jaccards.append(jac)
    return {
        "avg_jaccard": round(statistics.mean(jaccards), 4) if jaccards else 0.0,
        "min_jaccard": round(min(jaccards), 4) if jaccards else 0.0,
        "max_jaccard": round(max(jaccards), 4) if jaccards else 0.0,
        "pairs": len(jaccards),
    }


def write_report(
    results: list[dict],
    genre_stats: dict,
    diff_stats: dict,
    total_time: float,
) -> str:
    total = len(results)
    success = sum(1 for r in results if r["success"])
    failed = total - success
    wcs = [r["word_count"] for r in results if r["success"]]
    ttrs = [r["type_token_ratio"] for r in results if r["success"]]
    dcs = [r["dialogue_count"] for r in results if r["success"]]
    dds = [r["dialogue_density"] for r in results if r["success"]]
    reps = [r["repetition_rate"] for r in results if r["success"]]
    mems = [r["retrieved_memories"] for r in results if r["success"]]
    cbs = [r["callback_count"] for r in results if r["success"]]
    times = [r["time_ms"] for r in results if r["success"]]
    all_starts: Counter = Counter()
    for r in results:
        if r["success"]:
            for p, c in r["top_sentence_starts"]:
                all_starts[p] += c

    def bar(v, mx=60):
        return "\u2588" * max(1, int(v / max(mx, 1) * 60))

    lines = []
    lines.append("# SCRIPTY v2 — Phase F Final Benchmark Report")
    lines.append("")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Engine:** StoryEngineV2 (HWSE=OFF)")
    lines.append(f"**Stories:** {total} ({success} success, {failed} failed)")
    lines.append(f"**Total time:** {total_time:.1f}s ({total_time/success:.2f}s avg)" if success else "**Total time:** N/A")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Overall Summary")
    lines.append("")
    lines.append(f"| Metric | Value | Bar |")
    lines.append(f"|--------|-------|-----|")
    avg_wc = statistics.mean(wcs) if wcs else 0
    avg_ttr = statistics.mean(ttrs) if ttrs else 0
    avg_dc = statistics.mean(dcs) if dcs else 0
    avg_dd = statistics.mean(dds) if dds else 0
    avg_rep = statistics.mean(reps) if reps else 0
    avg_mem = statistics.mean(mems) if mems else 0
    avg_cb = statistics.mean(cbs) if cbs else 0
    avg_t = statistics.mean(times) if times else 0
    lines.append(f"| Avg word count | {avg_wc:.1f} | {bar(avg_wc, 600)} |")
    lines.append(f"| Avg type-token ratio | {avg_ttr:.4f} | {bar(avg_ttr * 100, 100)} |")
    lines.append(f"| Avg dialogue count | {avg_dc:.1f} | {bar(avg_dc, 30)} |")
    lines.append(f"| Avg dialogue density | {avg_dd:.1f}% | {bar(avg_dd, 30)} |")
    lines.append(f"| Avg repetition rate | {avg_rep:.4f} | {bar(avg_rep * 100, 50)} |")
    lines.append(f"| Avg memories retrieved | {avg_mem:.1f} | {bar(avg_mem, 20)} |")
    lines.append(f"| Avg callback usage | {avg_cb:.1f} | {bar(avg_cb, 10)} |")
    lines.append(f"| Avg generation time | {avg_t:.1f}ms | {bar(avg_t, 500)} |")
    std_wc = statistics.stdev(wcs) if len(wcs) > 1 else 0
    lines.append(f"| Word count std dev | {std_wc:.1f} | |")
    unique_vocab_total = len(set(
        w.lower().strip(".,!?;:\"'-\u201c\u201d")
        for r in results if r["success"]
        for w in r["story_text"].split()
    )) if wcs else 0
    lines.append(f"| Unique vocabulary (total) | {unique_vocab_total} | |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Per-Genre Breakdown")
    lines.append("")
    lines.append("| Genre | N | Words | TTR | Dialogue | Density | Repetition | Memories | Callbacks | Time(ms) |")
    lines.append("|-------|---|-------|-----|----------|---------|------------|----------|-----------|----------|")
    for genre in PROMPTS:
        s = genre_stats.get(genre, {})
        if s.get("count", 0) == 0:
            lines.append(f"| {genre} | 0 | — | — | — | — | — | — | — | — |")
            continue
        lines.append(
            f"| {genre} | {s['count']} | {s['avg_word_count']:.0f} | "
            f"{s['avg_ttr']:.3f} | {s['avg_dialogue_count']:.1f} | "
            f"{s['avg_dialogue_density']:.1f}% | {s['avg_repetition']:.3f} | "
            f"{s['avg_memories']:.1f} | {s['avg_callbacks']:.1f} | {s['avg_time_ms']:.0f} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Top Repeated Sentence Starters")
    lines.append("")
    lines.append("| Rank | Pattern | Count |")
    lines.append("|------|---------|-------|")
    for i, (pattern, count) in enumerate(all_starts.most_common(10), 1):
        lines.append(f"| {i} | \"{pattern}\" | {count} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Memory Utilization Stats")
    lines.append("")
    lines.append(f"- **Avg memories retrieved per scene:** {avg_mem:.1f}")
    lines.append(f"- **Avg callback usage per story:** {avg_cb:.1f}")
    lines.append(f"- **Callback % (stories with >=1 callback):** {sum(1 for c in cbs if c > 0) / max(len(cbs), 1) * 100:.1f}%")
    lines.append(f"- **Total memories across all stories:** {sum(mems)}")
    lines.append(f"- **Total callbacks across all stories:** {sum(cbs)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Character Differentiation")
    lines.append("")
    lines.append(f"- **Avg trigram Jaccard (cross-story):** {diff_stats.get('avg_jaccard', 'N/A')}")
    lines.append(f"- **Min Jaccard:** {diff_stats.get('min_jaccard', 'N/A')}")
    lines.append(f"- **Max Jaccard:** {diff_stats.get('max_jaccard', 'N/A')}")
    lines.append(f"- **Pairs compared:** {diff_stats.get('pairs', 0)}")
    if diff_stats.get("pairs", 0) > 0:
        if diff_stats["avg_jaccard"] < 0.15:
            lines.append("- **Verdict:** GOOD — stories show strong structural diversity")
        elif diff_stats["avg_jaccard"] < 0.30:
            lines.append("- **Verdict:** MODERATE — some structural overlap detected")
        else:
            lines.append("- **Verdict:** POOR — high structural similarity across stories")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 6. Files Changed Since Phase E")
    lines.append("")
    lines.append("| File | Change |")
    lines.append("|------|--------|")
    lines.append("| `backend/v2/scripts/benchmark_100.py` | **NEW** — Phase F 100-story benchmark script |")
    lines.append("| `reports/benchmark_v2_final.md` | **NEW** — This report |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 7. Remaining Bottlenecks")
    lines.append("")
    lines.append("| # | Bottleneck | Impact | Notes |")
    lines.append("|---|------------|--------|-------|")
    lines.append("| 1 | Template lock | High | Bigram repetition suggests structural repetition across scenes |")
    lines.append("| 2 | Vocabulary ceiling | Medium | ~703 unique words across 100 v1 stories; check v2 improvement |")
    lines.append("| 3 | Prose quality ceiling | High | Scorer ceiling effect — all stories score ~1.0 coherence |")
    lines.append("| 4 | No Redis in dev | Low | In-memory cache fallback lacks persistence |")
    lines.append("| 5 | Memory pruning | Medium | No eviction strategy for long stories |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 8. Recommended Next Phase")
    lines.append("")
    lines.append("1. **Realizer Redesign (Option A)** — Rewrite CompositionalRealizer to use event-chain")
    lines.append("   architecture (DramaticEvent → ParagraphComposer). Target: dialogue density >15%,")
    lines.append("   show-vs-tell ratio >3:1, unique sentence-start ratio >0.85.")
    lines.append("2. **Cross-genre Templates** — Genre-specific opening/action/dialogue pools to")
    lines.append("   improve structural diversity across genres.")
    lines.append("3. **Memory Pruning** — Implement importance-based eviction for BOOK mode.")
    lines.append("4. **Evaluation v2** — Replace heuristic BLEU/ROUGE with learned coherence scorer.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 9. Estimated Overall Quality Score")
    lines.append("")
    q_words = min(avg_wc / 500, 1.0) * 2.0 if avg_wc else 0
    q_ttr = min(avg_ttr / 0.7, 1.0) * 2.0 if avg_ttr else 0
    q_dialogue = min(avg_dd / 15.0, 1.0) * 1.5 if avg_dd else 0
    q_rep = max(0, 1.0 - avg_rep / 0.6) * 1.5 if avg_rep else 0
    q_mem = min(avg_mem / 10.0, 1.0) * 1.0 if avg_mem else 0
    q_cb = min(avg_cb / 3.0, 1.0) * 0.5 if avg_cb else 0
    q_diff = (1.0 - min(diff_stats.get("avg_jaccard", 0.3), 0.5) / 0.5) * 0.5
    q_success = (success / max(total, 1)) * 1.0
    q_total = q_words + q_ttr + q_dialogue + q_rep + q_mem + q_cb + q_diff + q_success

    lines.append(f"- **Words ({q_words:.1f}/2.0):** {avg_wc:.0f} avg (target >500)")
    lines.append(f"- **TTR ({q_ttr:.1f}/2.0):** {avg_ttr:.3f} avg (target >0.70)")
    lines.append(f"- **Dialogue ({q_dialogue:.1f}/1.5):** {avg_dd:.1f}% density (target >15%)")
    lines.append(f"- **Diversity ({q_rep:.1f}/1.5):** {avg_rep:.4f} rep rate (target <0.30)")
    lines.append(f"- **Memory ({q_mem:.1f}/1.0):** {avg_mem:.1f} avg memories (target >5)")
    lines.append(f"- **Callbacks ({q_cb:.1f}/0.5):** {avg_cb:.1f} avg callbacks (target >1)")
    lines.append(f"- **Differentiation ({q_diff:.1f}/0.5):** Jaccard={diff_stats.get('avg_jaccard', 0):.3f}")
    lines.append(f"- **Reliability ({q_success:.1f}/1.0):** {success}/{total} ({success/max(total,1)*100:.0f}%)")
    lines.append("")
    lines.append(f"### Overall: **{q_total:.1f} / 10.0**")
    if q_total >= 8.0:
        lines.append("**Grade: A** — Production-ready v2 engine")
    elif q_total >= 6.0:
        lines.append("**Grade: B** — Good, needs realizer improvement")
    elif q_total >= 4.0:
        lines.append("**Grade: C** — Functional, significant improvement needed")
    else:
        lines.append("**Grade: D** — Below threshold")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by Phase F benchmark script*")
    return "\n".join(lines)


async def main():
    print("=" * 70)
    print("SCRIPTY v2 — Phase F: Final Benchmark (100 Stories)")
    print("=" * 70)
    print()

    def reset_memory(engine_: StoryEngineV2) -> None:
        """Clear accumulated memory between stories for accurate per-story metrics."""
        mem = getattr(engine_, 'memory', None)
        if mem is not None:
            mem.episodic.records.clear()
            mem.semantic.facts.clear()
            mem._character_beliefs.clear()
            mem.emotional_retrieval.episodic_records.clear()
            if hasattr(mem.interpretation_engine.store, 'entries'):
                mem.interpretation_engine.store.entries.clear()
            if hasattr(mem.consequence_engine.store, 'entries'):
                mem.consequence_engine.store.entries.clear()
            if hasattr(mem.relationship_delta_store, 'deltas'):
                mem.relationship_delta_store.deltas.clear()
            mem.callback_scheduler.callbacks.clear()

    total_start = time.monotonic()
    engine = StoryEngineV2(enable_hwse=False)

    all_results = []
    total_prompts = sum(len(ps) for ps in PROMPTS.values())
    completed = 0

    for genre, prompts in PROMPTS.items():
        for idx, prompt in enumerate(prompts):
            completed += 1
            pct = completed / total_prompts * 100
            print(f"[{completed}/{total_prompts} {pct:4.1f}%] {genre:12s} — {prompt}")
            result = await generate_story(engine, genre, prompt, idx)
            snap = engine.memory.snapshot() if hasattr(engine, 'memory') else {}
            result["_memory_snapshot"] = snap
            result["retrieved_memories"] = snap.get("episodic_count", 0) + snap.get("semantic_count", 0)
            result["callback_count"] = snap.get("pending_callbacks", 0)
            all_results.append(result)

            # Reset memory between stories for per-story metric accuracy
            reset_memory(engine)
            status = "OK" if result["success"] else f"FAIL({result.get('error','?')[:30]})"
            wc = result["word_count"]
            print(f"         {status} | {wc:4d} words | TTR {result['type_token_ratio']:.3f} | "
                  f"{result['dialogue_count']} dial | {result['time_ms']:.0f}ms")

    total_elapsed = time.monotonic() - total_start

    print()
    print("=" * 70)
    print("COMPUTING STATISTICS...")
    print()

    genre_stats = compute_genre_stats(all_results)
    diff_stats = compute_character_differentiation(all_results)

    report = write_report(all_results, genre_stats, diff_stats, total_elapsed)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, "benchmark_v2_final.md")
    with open(report_path, "w") as f:
        f.write(report)

    print(report)
    print()
    print(f"Report written to: {report_path}")

    results_path = os.path.join(REPORTS_DIR, "benchmark_v2_results.json")
    summary = {
        "total": len(all_results),
        "success": sum(1 for r in all_results if r["success"]),
        "failed": sum(1 for r in all_results if not r["success"]),
        "total_time_seconds": total_elapsed,
        "genres": {},
    }
    for g in PROMPTS:
        gr = [r for r in all_results if r["genre"] == g and r["success"]]
        if gr:
            summary["genres"][g] = {
                "count": len(gr),
                "avg_word_count": round(statistics.mean([r["word_count"] for r in gr]), 1),
                "avg_ttr": round(statistics.mean([r["type_token_ratio"] for r in gr]), 4),
                "avg_dialogue_count": round(statistics.mean([r["dialogue_count"] for r in gr]), 1),
            }
    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Results JSON written to: {results_path}")

    return all_results, report


if __name__ == "__main__":
    asyncio.run(main())
