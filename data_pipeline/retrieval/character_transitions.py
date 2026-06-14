"""
Character Transition Mining — tracks belief / goal / relationship /
emotional state changes across a character's arc.
Output: character_transition_dataset.jsonl
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BELIEF_INDICATORS = [
    r"\b(believe|believed|think|thought|know|knew|realize|realized|understand|understood)\b",
    r"\b(i (was|am) wrong)\b", r"\b(i used to)\b", r"\b(now i (see|know|understand))\b",
    r"\b(it (was|is) (clear|obvious))\b",
]

GOAL_INDICATORS = [
    r"\b(i (need|must|have to|will|shall|intend|want))\b",
    r"\b(my (mission|purpose|goal|plan|aim|task|quest))\b",
    r"\b(i (will|shall) (find|get|reach|achieve|complete))\b",
    r"\b(i (swore|promised|vowed))\b",
]

RELATIONSHIP_INDICATORS = [
    r"\b(i (trust|distrust|love|hate|miss|forgive|resent))\b",
    r"\b(we (are|were) (friends|allies|enemies|partners))\b",
    r"\b(he|she) (was|is) (like|my)\b.*\b(brother|sister|friend|enemy|ally|mentor)\b",
    r"\b(i (no longer|still) (trust|love|hate))\b",
]

EMOTION_TRANSITION_INDICATORS = [
    r"\b(i (feel|felt|am|was) (no longer|not))\b",
    r"\b(the (fear|anger|joy|sadness|hope) (was|is) (gone|over|replaced))\b",
    r"\b(something (changed|shifted|broke))\b",
    r"\b(now (i|she|he) (feel|felt))\b",
]


class CharacterTransitionMiner:
    def __init__(self, source_path: str, output_dir: str = "reports/corpus_audit"):
        self.source_path = Path(source_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fragments: List[dict] = []
        self.transitions: List[dict] = []
        self._load()

    def _load(self):
        if self.source_path.exists():
            with open(self.source_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.fragments.append(json.loads(line))
        logger.info(f"Loaded {len(self.fragments)} fragments for character transitions")

    def _extract_characters(self, frag: dict) -> List[str]:
        participants = frag.get("participants", [])
        speaker = frag.get("speaker", "")
        target = frag.get("target", "")
        chars = set()
        if speaker:
            chars.add(speaker)
        if target:
            chars.add(target)
        for p in participants:
            if p and p[0].isupper():
                chars.add(p)
        return [c for c in chars if c and len(c) > 1]

    def _extract_belief_changes(self, text: str) -> List[str]:
        changes = []
        for m in re.finditer(BELIEF_INDICATORS[0], text.lower()):
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            snippet = text[start:end].strip()
            changes.append(snippet)
        other_patterns = BELIEF_INDICATORS[1:]
        if any(re.search(p, text.lower()) for p in other_patterns):
            for p in other_patterns:
                m = re.search(p, text.lower())
                if m:
                    start = max(0, m.start() - 20)
                    end = min(len(text), m.end() + 20)
                    changes.append(text[start:end].strip())
        return changes

    def _extract_goal_changes(self, text: str) -> List[str]:
        changes = []
        for p in GOAL_INDICATORS:
            m = re.search(p, text.lower())
            if m:
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 30)
                changes.append(text[start:end].strip())
        return changes

    def _extract_relationship_changes(self, text: str) -> List[str]:
        changes = []
        for p in RELATIONSHIP_INDICATORS:
            m = re.search(p, text.lower())
            if m:
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 20)
                changes.append(text[start:end].strip())
        return changes

    def _extract_emotional_changes(self, text: str, emotion: str) -> List[str]:
        changes = []
        for p in EMOTION_TRANSITION_INDICATORS:
            m = re.search(p, text.lower())
            if m:
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 20)
                changes.append(text[start:end].strip())
        if emotion:
            changes.append(f"expressed emotion: {emotion}")
        return changes

    def mine_all(self) -> List[dict]:
        self.transitions = []
        character_arcs = defaultdict(list)

        for frag in self.fragments:
            chars = self._extract_characters(frag)
            for ch in chars:
                character_arcs[ch].append(frag)

        for character, frags in character_arcs.items():
            frags.sort(key=lambda f: (f.get("chapter", 0), f.get("scene", 0),
                                      f.get("paragraph", 0)))

            prev_emotion = None
            for i, frag in enumerate(frags):
                text = frag.get("text", "")
                emotion = frag.get("emotion", "")
                belief_changes = self._extract_belief_changes(text)
                goal_changes = self._extract_goal_changes(text)
                relationship_changes = self._extract_relationship_changes(text)
                emotional_changes = self._extract_emotional_changes(text, emotion)

                is_transition = (
                    bool(belief_changes)
                    or bool(goal_changes)
                    or bool(relationship_changes)
                    or (prev_emotion and emotion and emotion != prev_emotion)
                )

                if is_transition:
                    entry = {
                        "id": frag.get("id", ""),
                        "character": character,
                        "source_book": frag.get("source_book", ""),
                        "chapter": frag.get("chapter", 0),
                        "scene": frag.get("scene", 0),
                        "paragraph": frag.get("paragraph", 0),
                        "emotion": emotion,
                        "prev_emotion": prev_emotion or "",
                        "transition_type": self._classify_transition(
                            bool(belief_changes), bool(goal_changes),
                            bool(relationship_changes),
                            prev_emotion and emotion and emotion != prev_emotion),
                        "belief_changes": belief_changes[:3],
                        "goal_changes": goal_changes[:3],
                        "relationship_changes": relationship_changes[:3],
                        "emotional_changes": emotional_changes[:3],
                        "text_snippet": text[:200],
                        "tension": frag.get("tension", 0),
                        "stakes": frag.get("stakes", 0),
                    }
                    self.transitions.append(entry)

                prev_emotion = emotion

        output_path = self.output_dir / "character_transition_dataset.jsonl"
        with open(output_path, "w") as f:
            for entry in self.transitions:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(self.transitions)} character transitions to {output_path}")
        return self.transitions

    @staticmethod
    def _classify_transition(belief: bool, goal: bool, relationship: bool,
                             emotion_shift: bool) -> str:
        types = []
        if belief:
            types.append("belief")
        if goal:
            types.append("goal")
        if relationship:
            types.append("relationship")
        if emotion_shift:
            types.append("emotional")
        return "+".join(types) if types else "unknown"

    def generate_report(self) -> dict:
        self.mine_all()
        transition_types = Counter(e["transition_type"] for e in self.transitions)
        characters = set(e["character"] for e in self.transitions)

        avg_tension = sum(e.get("tension", 0) for e in self.transitions) / max(1, len(self.transitions))
        avg_stakes = sum(e.get("stakes", 0) for e in self.transitions) / max(1, len(self.transitions))

        transitions_per_char = Counter(e["character"] for e in self.transitions)
        top_chars = transitions_per_char.most_common(10)

        report = {
            "total_transitions": len(self.transitions),
            "unique_characters": len(characters),
            "transition_type_distribution": dict(transition_types.most_common()),
            "average_tension": round(avg_tension, 4),
            "average_stakes": round(avg_stakes, 4),
            "top_characters_by_transitions": [(c, cnt) for c, cnt in top_chars],
        }

        report_path = self.output_dir / "character_transition_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Wrote character transition report to {report_path}")

        md_path = self.output_dir / "character_transition_report.md"
        lines = ["# Character Transition Report\n",
                 f"**Total Transitions**: {report['total_transitions']}\n",
                 f"**Unique Characters**: {report['unique_characters']}\n",
                 f"**Average Tension**: {report['average_tension']:.4f}\n",
                 f"**Average Stakes**: {report['average_stakes']:.4f}\n",
                 "\n## Transition Type Distribution\n",
                 "| Type | Count |\n|------|-------|\n"]
        for tt, cnt in sorted(transition_types.items(), key=lambda x: -x[1]):
            lines.append(f"| {tt} | {cnt} |\n")
        lines.append("\n## Top Characters by Transition Count\n| Character | Transitions |\n|-----------|-------------|\n")
        for ch, cnt in top_chars:
            lines.append(f"| {ch} | {cnt} |\n")
        with open(md_path, "w") as f:
            f.writelines(lines)
        logger.info(f"Wrote {md_path}")
        return report


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "reports/corpus_audit"
    miner = CharacterTransitionMiner(source, output)
    miner.generate_report()
