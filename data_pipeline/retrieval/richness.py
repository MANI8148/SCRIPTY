"""
Fragment Richness Audit — assigns reusability, dramatic_value,
character_signal, retrieval_value scores (0–1) per fragment.
Elite threshold = 0.85.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ELITE_THRESHOLD = 0.85


class FragmentRichnessAuditor:
    def __init__(self, source_path: str, output_dir: str = "reports/corpus_audit",
                 output_file: str = "fragment_richness.jsonl"):
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = self.output_dir / output_file
        self.fragments: List[dict] = []
        self.richness_scores: List[dict] = []
        self._load()

    def _load(self):
        if self.source_path.exists():
            with open(self.source_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.fragments.append(json.loads(line))
        logger.info(f"Loaded {len(self.fragments)} fragments for richness audit")

    def compute_reusability(self, frag: dict) -> float:
        qs = frag.get("quality_score", 0)
        ei = frag.get("emotion_intensity", 0)
        tl = frag.get("tension", 0)
        sk = frag.get("stakes", 0)
        return min(1.0, (qs * 0.4 + ei * 0.2 + tl * 0.2 + sk * 0.2))

    def compute_dramatic_value(self, frag: dict) -> float:
        tl = frag.get("tension", 0)
        sk = frag.get("stakes", 0)
        ei = frag.get("emotion_intensity", 0)
        return min(1.0, (tl * 0.4 + sk * 0.35 + ei * 0.25))

    def compute_character_signal(self, frag: dict) -> float:
        score = 0.0
        if frag.get("participants"):
            score += 0.2
        if frag.get("speaker"):
            score += 0.15
        if frag.get("target"):
            score += 0.1
        if frag.get("relationship_type"):
            score += 0.15
        if frag.get("conflict_type"):
            score += 0.1
        if frag.get("goal"):
            score += 0.1
        if frag.get("motivation"):
            score += 0.1
        if frag.get("emotion"):
            score += 0.1
        return min(1.0, score)

    def compute_retrieval_value(self, frag: dict) -> float:
        score = 0.0
        if frag.get("keywords"):
            score += 0.2
        if frag.get("retrieval_tags"):
            score += 0.2
        if frag.get("genre_tags"):
            score += 0.1
        if frag.get("emotion_tags"):
            score += 0.1
        if frag.get("embedding"):
            score += 0.2
        if frag.get("scene_role"):
            score += 0.1
        if frag.get("narrative_function"):
            score += 0.1
        return min(1.0, score)

    def compute_combined(self, frag: dict) -> float:
        r = self.compute_reusability(frag)
        d = self.compute_dramatic_value(frag)
        c = self.compute_character_signal(frag)
        v = self.compute_retrieval_value(frag)
        return min(1.0, r * 0.3 + d * 0.3 + c * 0.2 + v * 0.2)

    def audit_all(self) -> List[dict]:
        self.richness_scores = []
        for frag in self.fragments:
            entry = {
                "id": frag.get("id", ""),
                "source_book": frag.get("source_book", ""),
                "category": frag.get("category", ""),
                "subcategory": frag.get("subcategory", ""),
                "reusability": round(self.compute_reusability(frag), 4),
                "dramatic_value": round(self.compute_dramatic_value(frag), 4),
                "character_signal": round(self.compute_character_signal(frag), 4),
                "retrieval_value": round(self.compute_retrieval_value(frag), 4),
                "combined_score": round(self.compute_combined(frag), 4),
                "is_elite": self.compute_combined(frag) >= ELITE_THRESHOLD,
                "quality_score": frag.get("quality_score", 0),
                "emotion": frag.get("emotion", ""),
                "tension": frag.get("tension", 0),
                "stakes": frag.get("stakes", 0),
            }
            self.richness_scores.append(entry)

        with open(self.output_path, "w") as f:
            for entry in self.richness_scores:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(self.richness_scores)} richness entries to {self.output_path}")

        elite = [e for e in self.richness_scores if e["is_elite"]]
        logger.info(f"Elite fragments: {len(elite)}/{len(self.richness_scores)} (threshold={ELITE_THRESHOLD})")
        return self.richness_scores

    def generate_report(self) -> dict:
        self.audit_all()
        scores = [e["combined_score"] for e in self.richness_scores]
        elite_count = sum(1 for e in self.richness_scores if e["is_elite"])

        avg_by_cat = {}
        for e in self.richness_scores:
            cat = e.get("category", "unknown")
            if cat not in avg_by_cat:
                avg_by_cat[cat] = []
            avg_by_cat[cat].append(e["combined_score"])

        report = {
            "total_fragments": len(self.richness_scores),
            "elite_fragments": elite_count,
            "elite_ratio": round(elite_count / max(1, len(self.richness_scores)), 4),
            "mean_combined_score": round(sum(scores) / max(1, len(scores)), 4),
            "min_combined_score": round(min(scores), 4) if scores else 0,
            "max_combined_score": round(max(scores), 4) if scores else 0,
            "mean_reusability": round(
                sum(e["reusability"] for e in self.richness_scores) / max(1, len(self.richness_scores)), 4),
            "mean_dramatic_value": round(
                sum(e["dramatic_value"] for e in self.richness_scores) / max(1, len(self.richness_scores)), 4),
            "mean_character_signal": round(
                sum(e["character_signal"] for e in self.richness_scores) / max(1, len(self.richness_scores)), 4),
            "mean_retrieval_value": round(
                sum(e["retrieval_value"] for e in self.richness_scores) / max(1, len(self.richness_scores)), 4),
            "avg_combined_by_category": {cat: round(sum(vs) / len(vs), 4) for cat, vs in avg_by_cat.items()},
        }

        report_path = self.output_dir / "fragment_richness_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Wrote richness report to {report_path}")

        md_path = self.output_dir / "fragment_richness_audit.md"
        lines = ["# Fragment Richness Audit\n",
                 f"**Total Fragments**: {report['total_fragments']}\n",
                 f"**Elite Fragments** (≥{ELITE_THRESHOLD}): {report['elite_fragments']} ({report['elite_ratio']:.1%})\n",
                 f"**Mean Combined Score**: {report['mean_combined_score']:.4f}\n",
                 f"**Mean Reusability**: {report['mean_reusability']:.4f}\n",
                 f"**Mean Dramatic Value**: {report['mean_dramatic_value']:.4f}\n",
                 f"**Mean Character Signal**: {report['mean_character_signal']:.4f}\n",
                 f"**Mean Retrieval Value**: {report['mean_retrieval_value']:.4f}\n",
                 "\n## Avg Combined Score by Category\n",
                 "| Category | Score |\n|----------|-------|\n"]
        for cat, sc in sorted(report["avg_combined_by_category"].items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | {sc:.4f} |\n")
        with open(md_path, "w") as f:
            f.writelines(lines)
        logger.info(f"Wrote {md_path}")
        return report


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "reports/corpus_audit"
    auditor = FragmentRichnessAuditor(source, output)
    auditor.generate_report()
