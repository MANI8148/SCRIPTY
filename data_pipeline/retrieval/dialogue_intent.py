"""
Dialogue Intent Discovery — classifies dialogue fragments into
threat / persuasion / confession / warning / question / command /
comfort / deception / bargain / flirtation intents.
"""
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DIALOGUE_INTENTS = [
    "threat", "persuasion", "confession", "warning", "question",
    "command", "comfort", "deception", "bargain", "flirtation",
]

INTENT_PATTERNS = {
    "threat": {
        "primary": [
            r"\b(or else)\b", r"\b(will regret)\b", r"\b(better (not|watch))\b",
            r"\b(i'?ll (make|destroy|end|kill))\b", r"\b(you (will|won'?t) (like|survive))\b",
            r"\b(don'?t (test|try|push))\b", r"\b(last warning)\b",
            r"\b(this is your (last|final))\b", r"\b(i swear)\b.*\b(will)\b",
            r"\b(pay for)\b", r"\b(suffer)\b",
        ],
        "secondary": ["threat", "warning", "danger", "hurt", "destroy", "kill"],
        "weight": 1.0,
    },
    "persuasion": {
        "primary": [
            r"\b(you should)\b", r"\b(just think)\b", r"\b(consider)\b",
            r"\b(it (would|will) be (better|worth))\b", r"\b(imagine)\b",
            r"\b(think about)\b", r"\b(what if)\b", r"\b(you (could|can))\b",
            r"\b(i (believe|think) you)\b", r"\b(hear me out)\b",
        ],
        "secondary": ["convince", "persuade", "please", "advantage", "benefit"],
        "weight": 0.9,
    },
    "confession": {
        "primary": [
            r"\b(i (confess|admit))\b", r"\b(the truth is)\b", r"\b(i lied)\b",
            r"\b(i was the one)\b", r"\b(it was me)\b", r"\b(i (need|have) to tell)\b",
            r"\b(i can'?t hide)\b", r"\b(i'?m (sorry|afraid) i)\b",
            r"\b(the secret is)\b", r"\b(i (should|must) (confess|tell))\b",
        ],
        "secondary": ["confess", "admit", "truth", "secret", "guilty", "blame"],
        "weight": 1.0,
    },
    "warning": {
        "primary": [
            r"\b(beware)\b", r"\b(caution)\b", r"\b(don'?t (go|do|say|touch|trust))\b",
            r"\b(stop right)\b", r"\b(i warn)\b", r"\b(be careful)\b",
            r"\b(watch (out|your))\b", r"\b(if you (value|know))\b",
            r"\b(you have been warned)\b", r"\b(listen carefully)\b",
        ],
        "secondary": ["caution", "danger", "careful", "warning", "beware"],
        "weight": 0.9,
    },
    "question": {
        "primary": [
            r"\?$", r"^(who|what|when|where|why|how|did|do|does|is|are|was|were|can|could|will|would|shall|should|have|has|had)\b",
            r"\b(tell me)\b", r"\b(do you know)\b", r"\b(have you)\b",
        ],
        "secondary": ["?", "ask", "wonder", "curious"],
        "weight": 0.8,
    },
    "command": {
        "primary": [
            r"^(do it|go|come|stop|listen|look|tell me|give me|leave|stay|run|fight|wait|help|follow)\b",
            r"\b(i (order|command) you)\b", r"\b(you will)\b",
            r"\b(don'?t (you )?(dare|move|speak|make))\b",
            r"\b(stand (down|up|aside))\b",
        ],
        "secondary": ["order", "command", "now", "immediately", "must"],
        "weight": 0.8,
    },
    "comfort": {
        "primary": [
            r"\b(it'?s (okay|all right|alright))\b", r"\b(you'?ll be fine)\b",
            r"\b(shh|shush)\b", r"\b(i'?m here)\b", r"\b(everything will)\b",
            r"\b(don'?t (cry|worry|be afraid))\b", r"\b(there there)\b",
            r"\b(it (wasn'?t|was not) your fault)\b", r"\b(you did (your|what you))\b",
            r"\b(let it out)\b",
        ],
        "secondary": ["comfort", "safe", "okay", "fine", "alright", "peace"],
        "weight": 1.0,
    },
    "deception": {
        "primary": [
            r"\b(i (swear|promise))\b", r"\b(that'?s not true)\b",
            r"\b(i (never|didn'?t|did not))\b", r"\b(you (misunderstand|have it wrong))\b",
            r"\b(it (wasn'?t|was not) me)\b", r"\b(i don'?t know what)\b",
            r"\b(they'?re lying)\b", r"\b(believe me)\b",
            r"\b(i (would|wouldn'?t) never)\b",
        ],
        "secondary": ["lie", "deceive", "false", "never", "swear", "promise", "trust me"],
        "weight": 0.9,
    },
    "bargain": {
        "primary": [
            r"\b(i'?ll (give|offer|trade|tell))\b", r"\b(in exchange)\b",
            r"\b(deal\?|it'?s a deal|you have a deal)\b",
            r"\b(if you (do|help|give|tell))\b", r"\b(consider this)\b",
            r"\b(what'?s (in it|your offer))\b", r"\b(counter[- ]?offer)\b",
            r"\b(how about)\b.*\b(trade|exchange|offer)\b",
            r"\b(i can (give|offer|do))\b.*\b(if)\b",
        ],
        "secondary": ["deal", "trade", "offer", "bargain", "negotiate", "exchange"],
        "weight": 1.0,
    },
    "flirtation": {
        "primary": [
            r"\b(you look (beautiful|handsome|gorgeous|lovely))\b",
            r"\b(i'?ve (been )?watching)\b", r"\b(i (like|love) the way)\b",
            r"\b(can i buy you)\b", r"\b(are you (single|free))\b",
            r"\b(i couldn'?t help)\b", r"\b(you'?re (different|special))\b",
            r"\b(what'?s a (beautiful|handsome) (person|man|woman) like)\b",
        ],
        "secondary": ["beautiful", "handsome", "charming", "flirt", "cute", "attractive"],
        "weight": 0.9,
    },
}


class DialogueIntentMiner:
    def __init__(self, source_path: str, output_dir: str = "reports/corpus_audit"):
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fragments: List[dict] = []
        self.intent_dataset: List[dict] = []
        self._load()

    def _load(self):
        if self.source_path.exists():
            with open(self.source_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.fragments.append(json.loads(line))
        logger.info(f"Loaded {len(self.fragments)} fragments for dialogue intent mining")

    def is_dialogue_fragment(self, frag: dict) -> bool:
        cat = frag.get("category", "").lower()
        if cat == "dialogue" or cat.startswith("dialogue_"):
            return True
        text = frag.get("text", "")
        if re.search(r'["\u201C\u2018]', text):
            return True
        return False

    def detect_intent(self, text: str) -> List[Tuple[str, float]]:
        text_lower = text.lower()
        scores = []
        for intent_name, config in INTENT_PATTERNS.items():
            score = 0.0
            max_primary = len(config["primary"])
            if max_primary > 0:
                primary_hits = sum(1 for p in config["primary"] if re.search(p, text_lower))
                score += (primary_hits / max_primary) * 0.7
            secondary_hits = sum(1 for kw in config["secondary"] if kw in text_lower)
            max_secondary = len(config["secondary"])
            if max_secondary > 0:
                score += (secondary_hits / max_secondary) * 0.3
            score *= config["weight"]
            if score > 0:
                scores.append((intent_name, round(min(score, 1.0), 4)))
        scores.sort(key=lambda x: -x[1])
        return scores

    def mine_all(self) -> List[dict]:
        self.intent_dataset = []
        dialogue_count = 0
        intent_counts = Counter()

        for frag in self.fragments:
            if not self.is_dialogue_fragment(frag):
                continue
            dialogue_count += 1
            text = frag.get("text", "")
            intents = self.detect_intent(text)
            primary_intent = intents[0][0] if intents else "unknown"
            primary_confidence = intents[0][1] if intents else 0.0

            entry = {
                "id": frag.get("id", ""),
                "source_book": frag.get("source_book", ""),
                "chapter": frag.get("chapter", 0),
                "text": text[:200],
                "primary_intent": primary_intent,
                "confidence": primary_confidence,
                "all_intents": intents[:3],
                "emotion": frag.get("emotion", ""),
                "speaker": frag.get("speaker", ""),
                "target": frag.get("target", ""),
                "tension": frag.get("tension", 0),
                "stakes": frag.get("stakes", 0),
            }
            self.intent_dataset.append(entry)
            intent_counts[primary_intent] += 1

        output_path = self.output_dir / "dialogue_intent_dataset.jsonl"
        with open(output_path, "w") as f:
            for entry in self.intent_dataset:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(self.intent_dataset)} dialogue intents to {output_path}")
        logger.info(f"Intent distribution: {dict(intent_counts.most_common())}")
        return self.intent_dataset

    def generate_report(self) -> dict:
        self.mine_all()
        intents_list = [e["primary_intent"] for e in self.intent_dataset]
        intent_dist = dict(Counter(intents_list).most_common())
        conf_by_intent = defaultdict(list)
        for e in self.intent_dataset:
            conf_by_intent[e["primary_intent"]].append(e["confidence"])

        report = {
            "total_dialogue_fragments": len(self.intent_dataset),
            "total_corpus_fragments": len(self.fragments),
            "dialogue_ratio": round(len(self.intent_dataset) / max(1, len(self.fragments)), 4),
            "intent_distribution": intent_dist,
            "avg_confidence_by_intent": {
                intent: round(sum(vals) / len(vals), 4)
                for intent, vals in conf_by_intent.items()
            },
        }

        report_path = self.output_dir / "dialogue_intent_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Wrote dialogue intent report to {report_path}")

        md_path = self.output_dir / "dialogue_intent_report.md"
        lines = ["# Dialogue Intent Report\n",
                 f"**Total Dialogue Fragments**: {report['total_dialogue_fragments']}\n",
                 f"**Dialogue Ratio**: {report['dialogue_ratio']:.1%}\n",
                 "\n## Intent Distribution\n",
                 "| Intent | Count |\n|--------|-------|\n"]
        for intent, cnt in sorted(intent_dist.items(), key=lambda x: -x[1]):
            lines.append(f"| {intent} | {cnt} |\n")
        lines.append("\n## Average Confidence by Intent\n| Intent | Confidence |\n|--------|------------|\n")
        for intent, ac in sorted(report["avg_confidence_by_intent"].items(), key=lambda x: -x[1]):
            lines.append(f"| {intent} | {ac:.4f} |\n")
        with open(md_path, "w") as f:
            f.writelines(lines)
        logger.info(f"Wrote {md_path}")
        return report


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "reports/corpus_audit"
    miner = DialogueIntentMiner(source, output)
    miner.generate_report()
