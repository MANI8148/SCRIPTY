"""
Scene Beat Mining — classifies each fragment's scene role and mines
openings / inciting_incidents / conflicts / reversals / revelations /
climaxes / resolutions / cliffhangers across the corpus.
"""
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SCENE_BEAT_CATEGORIES = [
    "opening", "inciting_incident", "conflict", "reversal",
    "revelation", "climax", "resolution", "cliffhanger",
]

BEAT_PATTERNS = {
    "opening": [
        r"\b(the (door|gate|day|morning|sun|rain|night) (opened|dawned|came|fell|began))\b",
        r"\b(it was a (cold|dark|stormy|beautiful|quiet|peaceful))\b",
        r"\b(chapter|part|book|prologue)\b",
        r"\b(once upon|in the beginning|long ago)\b",
        r"\b(she|he) (woke|stepped|entered|arrived|stood)\b",
    ],
    "inciting_incident": [
        r"\b(suddenly|without warning|out of nowhere|all at once|then)\b",
        r"\b(a (scream|crash|bang|knock|shout|cry))\b",
        r"\b(something (happened|crashed|broke|changed))\b",
        r"\b(the (message|letter|news|call|announcement))\b",
        r"\b(everything changed)\b",
    ],
    "conflict": [
        r"\b(argu|fight|battle|struggl|clash|confront)\b",
        r"\b(you (are|were) (wrong|mistaken|lying))\b",
        r"\b(i won'?t|you can'?t|nobody)\b",
        r"\b(how dare|what (do|are) you)\b",
        r"\b(tension|standoff|hostile|aggressive)\b",
    ],
    "reversal": [
        r"\b(but (then|suddenly|unexpectedly))\b",
        r"\b(however|yet|despite|although|nevertheless)\b",
        r"\b(turned (the tables|around|on))\b",
        r"\b(surpris|shock|unexpected|unforeseen)\b",
        r"\b(everything (he|she|they) thought)\b.*\b(wrong)\b",
    ],
    "revelation": [
        r"\b(reveal|discover|uncover|realiz|truth)\b",
        r"\b(i now (know|see|understand))\b",
        r"\b(the (truth|secret|answer|identity))\b",
        r"\b(it was (you|him|her|them))\b",
        r"\b(finally (understood|realized|saw|knew))\b",
    ],
    "climax": [
        r"\b(this is it|the moment|now or never|final (confrontation|battle))\b",
        r"\b(everything (depends|rides) on)\b",
        r"\b(the (fate|future|world) (hangs|rests))\b",
        r"\b(one last|final (effort|attempt|breath|stand))\b",
        r"\b(all or nothing)\b",
    ],
    "resolution": [
        r"\b(in the end|finally|at last|it was over)\b",
        r"\b(the (dust|smoke|silence|calm) (settled|fell))\b",
        r"\b(peace|relief|quiet|stillness)\b",
        r"\b(it was (done|finished|over|complete))\b",
        r"\b(they (survived|won|escaped|made it))\b",
    ],
    "cliffhanger": [
        r"\b(and then|to be continued)\b$",
        r"\b(\?\s*$|\!+\s*$|\.\.\.\s*$)",
        r"\b(suddenly|without warning)\b.*$",
        r"\b(before (he|she|they) could)\b",
        r"\b(nothing could (prepare|have))\b",
    ],
}


class SceneBeatMiner:
    def __init__(self, source_path: str, output_dir: str = "reports/corpus_audit"):
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fragments: List[dict] = []
        self.scene_beats: List[dict] = []
        self._load()

    def _load(self):
        if self.source_path.exists():
            with open(self.source_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.fragments.append(json.loads(line))
        logger.info(f"Loaded {len(self.fragments)} fragments for scene beat mining")

    def _get_scene_key(self, frag: dict) -> str:
        return f"{frag.get('source_book', '')}|{frag.get('chapter', 0)}|{frag.get('scene', 0)}"

    def detect_beats(self, text: str, frag: dict) -> List[Tuple[str, float]]:
        text_lower = text.lower()
        explicit_role = frag.get("scene_role", "").lower().strip()
        if explicit_role in SCENE_BEAT_CATEGORIES:
            return [(explicit_role, 1.0)]

        scores = []
        for beat, patterns in BEAT_PATTERNS.items():
            score = 0.0
            for p in patterns:
                if re.search(p, text_lower):
                    score += 0.25
            if score > 0:
                scores.append((beat, round(min(score, 1.0), 4)))
        scores.sort(key=lambda x: -x[1])
        return scores

    def mine_all(self) -> List[dict]:
        self.scene_beats = []
        beat_counts = Counter()
        scene_groups = defaultdict(list)

        for frag in self.fragments:
            scene_key = self._get_scene_key(frag)
            scene_groups[scene_key].append(frag)

        for frag in self.fragments:
            text = frag.get("text", "")
            beats = self.detect_beats(text, frag)
            primary_beat = beats[0][0] if beats else "unknown"
            primary_conf = beats[0][1] if beats else 0.0

            entry = {
                "id": frag.get("id", ""),
                "source_book": frag.get("source_book", ""),
                "chapter": frag.get("chapter", 0),
                "scene": frag.get("scene", 0),
                "paragraph": frag.get("paragraph", 0),
                "scene_key": self._get_scene_key(frag),
                "text_snippet": text[:200],
                "primary_beat": primary_beat,
                "confidence": primary_conf,
                "all_beats": beats[:3],
                "emotion": frag.get("emotion", ""),
                "tension": frag.get("tension", 0),
                "stakes": frag.get("stakes", 0),
                "category": frag.get("category", ""),
                "participants": frag.get("participants", []),
            }
            self.scene_beats.append(entry)
            beat_counts[primary_beat] += 1

        output_path = self.output_dir / "scene_beats_dataset.jsonl"
        with open(output_path, "w") as f:
            for entry in self.scene_beats:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(self.scene_beats)} scene beats to {output_path}")
        logger.info(f"Beat distribution: {dict(beat_counts.most_common())}")
        return self.scene_beats

    def generate_report(self) -> dict:
        self.mine_all()
        beats = [e["primary_beat"] for e in self.scene_beats]
        beat_dist = dict(Counter(beats).most_common())

        conf_by_beat = defaultdict(list)
        for e in self.scene_beats:
            conf_by_beat[e["primary_beat"]].append(e["confidence"])

        tension_by_beat = defaultdict(list)
        for e in self.scene_beats:
            tension_by_beat[e["primary_beat"]].append(e.get("tension", 0))

        report = {
            "total_beats": len(self.scene_beats),
            "total_fragments": len(self.fragments),
            "beat_distribution": beat_dist,
            "avg_confidence_by_beat": {
                b: round(sum(vals) / len(vals), 4)
                for b, vals in conf_by_beat.items()
            },
            "avg_tension_by_beat": {
                b: round(sum(vals) / len(vals), 4)
                for b, vals in tension_by_beat.items()
            },
        }

        report_path = self.output_dir / "scene_beats_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Wrote scene beats report to {report_path}")

        md_path = self.output_dir / "scene_beats_report.md"
        lines = ["# Scene Beats Report\n",
                 f"**Total Beats**: {report['total_beats']}\n",
                 f"**Total Fragments**: {report['total_fragments']}\n",
                 "\n## Beat Distribution\n",
                 "| Beat | Count |\n|------|-------|\n"]
        for beat, cnt in sorted(beat_dist.items(), key=lambda x: -x[1]):
            lines.append(f"| {beat} | {cnt} |\n")
        lines.append("\n## Average Confidence by Beat\n| Beat | Confidence |\n|------|------------|\n")
        for beat, ac in sorted(report["avg_confidence_by_beat"].items(), key=lambda x: -x[1]):
            lines.append(f"| {beat} | {ac:.4f} |\n")
        lines.append("\n## Average Tension by Beat\n| Beat | Tension |\n|------|---------|\n")
        for beat, at in sorted(report["avg_tension_by_beat"].items(), key=lambda x: -x[1]):
            lines.append(f"| {beat} | {at:.4f} |\n")
        with open(md_path, "w") as f:
            f.writelines(lines)
        logger.info(f"Wrote {md_path}")
        return report


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "reports/corpus_audit"
    miner = SceneBeatMiner(source, output)
    miner.generate_report()
