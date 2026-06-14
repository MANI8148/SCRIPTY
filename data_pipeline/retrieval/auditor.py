"""
Corpus Auditor — Generates per-category audit reports.
"""
import json
import logging
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Optional
import re

from data_pipeline.schema.fragment import NarrativeFragment

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

CATEGORY_GROUPS = {
    "dialogue_audit": ["dialogue", "dialogue_subtext", "dialogue_confessions", "dialogue_arguments",
                        "dialogue_threats", "dialogue_flirtation", "dialogue_negotiation"],
    "actions_audit": ["actions", "physical_actions", "goal_driven_actions", "investigation_actions",
                       "combat_actions", "social_actions"],
    "body_language_audit": ["body_language", "microexpressions", "facial_expressions",
                             "gestures", "movement_patterns"],
    "reactions_audit": ["reactions", "emotional_reactions", "physical_reactions", "social_reactions"],
    "conflicts_audit": ["conflicts", "internal_conflicts", "interpersonal_conflicts",
                         "group_conflicts", "institutional_conflicts", "moral_conflicts"],
    "relationships_audit": ["relationships", "friendships", "rivalries", "romances",
                             "family_relationships", "mentor_relationships", "betrayals"],
    "memory_audit": ["memories", "flashbacks", "trauma_memories", "nostalgic_memories",
                      "regret_memories", "victory_memories"],
    "scene_openings_audit": ["scene_openings", "scene_hooks"],
    "scene_endings_audit": ["scene_endings", "scene_cliffhangers"],
}


class CorpusAuditor:
    def __init__(self, source_path: str, output_dir: str = "reports/corpus_audit"):
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fragments: List[dict] = []
        self._load()

    def _load(self):
        if self.source_path.exists():
            with open(self.source_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.fragments.append(json.loads(line))
        logger.info(f"Loaded {len(self.fragments)} fragments")

    def _get_group(self, frag: dict, category_groups: dict) -> Optional[str]:
        cat = frag.get("category", "").lower()
        sub = frag.get("subcategory", "").lower()
        for group_name, cats in category_groups.items():
            if cat in cats or sub in cats:
                return group_name
        return None

    def _score_top_patterns(self, texts: List[str], top_n: int = 10) -> List[tuple]:
        patterns = Counter()
        for t in texts:
            sentences = re.split(r'[.!?]+', t.lower())
            for s in sentences:
                s = s.strip()
                words = s.split()
                if 3 <= len(words) <= 8:
                    trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
                    for tg in trigrams:
                        patterns[tg] += 1
        return patterns.most_common(top_n)

    def audit_group(self, group_name: str, category_list: List[str]) -> dict:
        group_frags = [f for f in self.fragments if self._get_group(f, {group_name: category_list}) == group_name]
        if not group_frags:
            return {"total": 0, "note": "No fragments in this category"}

        texts = [f.get("text", "") for f in group_frags]
        qualities = [f.get("quality_score", 0) for f in group_frags if f.get("quality_score")]
        emotions = [f.get("emotion", "") for f in group_frags if f.get("emotion")]
        cats = [f.get("subcategory", f.get("category", "")) for f in group_frags]
        tensions = [f.get("tension", 0) for f in group_frags if f.get("tension")]
        stakes = [f.get("stakes", 0) for f in group_frags if f.get("stakes")]

        unique_texts = set(t[:100].lower().strip() for t in texts)
        dup_ratio = 1 - (len(unique_texts) / max(1, len(texts)))

        avg_quality = sum(qualities) / len(qualities) if qualities else 0
        avg_tension = sum(tensions) / len(tensions) if tensions else 0
        avg_stakes = sum(stakes) / len(stakes) if stakes else 0

        emotion_dist = dict(Counter(emotions).most_common(10))
        category_dist = dict(Counter(cats).most_common())
        top_patterns = self._score_top_patterns(texts)

        strong_cats = sorted(
            [(c, sum(1 for f in group_frags if f.get("subcategory") == c or f.get("category") == c))
             for c in set(cats)],
            key=lambda x: -x[1]
        )[:5]

        return {
            "total_fragments": len(group_frags),
            "unique_fragments": len(unique_texts),
            "duplicate_ratio": round(dup_ratio, 3),
            "average_quality_score": round(avg_quality, 3),
            "average_tension": round(avg_tension, 3),
            "average_stakes": round(avg_stakes, 3),
            "emotion_distribution": emotion_dist,
            "category_distribution": category_dist,
            "top_repeated_patterns": [(p, c) for p, c in top_patterns],
            "strongest_categories": strong_cats[:3],
            "weakest_categories": strong_cats[-3:] if len(strong_cats) >= 3 else [],
        }

    def generate_all_reports(self):
        for group_name, category_list in CATEGORY_GROUPS.items():
            report = self.audit_group(group_name, category_list)
            output_path = self.output_dir / f"{group_name}.md"
            with open(output_path, 'w') as f:
                f.write(self._format_report(group_name, report, category_list))
            logger.info(f"Wrote {output_path}")

        summary_path = self.output_dir / "corpus_audit_summary.json"
        summary = self._generate_summary()
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Wrote {summary_path}")

    def _format_report(self, group_name: str, report: dict, categories: List[str]) -> str:
        lines = []
        lines.append(f"# Corpus Audit: {group_name.replace('_audit','').replace('_',' ').title()}\n")
        lines.append(f"**Categories**: {', '.join(categories)}\n")
        lines.append(f"**Total Fragments**: {report.get('total_fragments', 0)}\n")
        lines.append(f"**Unique Fragments**: {report.get('unique_fragments', 0)}\n")
        lines.append(f"**Duplicate Ratio**: {report.get('duplicate_ratio', 0):.1%}\n")
        lines.append(f"**Average Quality Score**: {report.get('average_quality_score', 0):.3f}\n")
        lines.append(f"**Average Tension**: {report.get('average_tension', 0):.3f}\n")
        lines.append(f"**Average Stakes**: {report.get('average_stakes', 0):.3f}\n")
        lines.append(f"\n## Emotion Distribution\n")
        lines.append(f"| Emotion | Count |\n|---------|-------|\n")
        for em, cnt in report.get("emotion_distribution", {}).items():
            lines.append(f"| {em} | {cnt} |\n")
        lines.append(f"\n## Category Distribution\n")
        lines.append(f"| Category | Count |\n|----------|-------|\n")
        for cat, cnt in report.get("category_distribution", {}).items():
            lines.append(f"| {cat} | {cnt} |\n")
        lines.append(f"\n## Top Repeated Patterns\n")
        for pat, cnt in report.get("top_repeated_patterns", []):
            lines.append(f"- \"{pat}\" ({cnt}x)\n")
        lines.append(f"\n## Strongest Categories\n")
        for cat, cnt in report.get("strongest_categories", []):
            lines.append(f"- {cat}: {cnt} fragments\n")
        lines.append(f"\n## Weakest Categories\n")
        for cat, cnt in report.get("weakest_categories", []):
            lines.append(f"- {cat}: {cnt} fragments\n")
        return "".join(lines)

    def _generate_summary(self) -> dict:
        summary = {}
        total = len(self.fragments)
        qualities = [f.get("quality_score", 0) for f in self.fragments if f.get("quality_score")]
        emotions = [f.get("emotion", "") for f in self.fragments if f.get("emotion")]
        categories = [f.get("category", "") for f in self.fragments]

        summary["total_fragments"] = total
        summary["average_quality"] = round(sum(qualities) / len(qualities), 3) if qualities else 0
        summary["categories_covered"] = len(set(categories))
        summary["emotions_covered"] = len(set(emotions))
        summary["top_emotions"] = dict(Counter(emotions).most_common(5))
        summary["top_categories"] = dict(Counter(categories).most_common(10))
        if total > 0:
            summary["fragments_with_tension"] = sum(1 for f in self.fragments if f.get("tension", 0) > 0)
            summary["fragments_with_stakes"] = sum(1 for f in self.fragments if f.get("stakes", 0) > 0)
            summary["fragments_with_emotion"] = sum(1 for f in self.fragments if f.get("emotion"))
            summary["fragments_with_participants"] = sum(1 for f in self.fragments if f.get("participants"))
        return summary


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "reports/corpus_audit"
    auditor = CorpusAuditor(source, output)
    auditor.generate_all_reports()
    print(f"Audit complete. Reports in {output}/")
