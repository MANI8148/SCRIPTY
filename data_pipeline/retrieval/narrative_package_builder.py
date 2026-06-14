"""
Narrative Package Builder — prototype that takes a narrative goal
(emotion, conflict, relationship, genre) and retrieves a curated
NarrativePackage with dialogue, actions, body_language, conflicts,
memories, and sensory_details.
"""
import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class NarrativePackage:
    def __init__(self, goal: str, emotion: str, conflict: str,
                 relationship: str, genre: str):
        self.goal = goal
        self.emotion = emotion
        self.conflict = conflict
        self.relationship = relationship
        self.genre = genre
        self.dialogue: List[dict] = []
        self.actions: List[dict] = []
        self.body_language: List[dict] = []
        self.conflicts: List[dict] = []
        self.memories: List[dict] = []
        self.sensory_details: List[dict] = []
        self.reactions: List[dict] = []
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "emotion": self.emotion,
            "conflict": self.conflict,
            "relationship": self.relationship,
            "genre": self.genre,
            "dialogue_count": len(self.dialogue),
            "actions_count": len(self.actions),
            "body_language_count": len(self.body_language),
            "conflicts_count": len(self.conflicts),
            "memories_count": len(self.memories),
            "sensory_details_count": len(self.sensory_details),
            "reactions_count": len(self.reactions),
            "total_fragments": (len(self.dialogue) + len(self.actions)
                                + len(self.body_language) + len(self.conflicts)
                                + len(self.memories) + len(self.sensory_details)
                                + len(self.reactions)),
            "dialogue": [f.get("text", "")[:200] for f in self.dialogue[:5]],
            "actions": [f.get("text", "")[:200] for f in self.actions[:5]],
            "body_language": [f.get("text", "")[:200] for f in self.body_language[:5]],
            "conflicts": [f.get("text", "")[:200] for f in self.conflicts[:5]],
            "memories": [f.get("text", "")[:200] for f in self.memories[:5]],
            "sensory_details": [f.get("text", "")[:200] for f in self.sensory_details[:5]],
            "reactions": [f.get("text", "")[:200] for f in self.reactions[:5]],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class NarrativePackageBuilder:
    def __init__(self, source_path: str = "data_pipeline/output/fragments_cleaned.jsonl",
                 output_dir: str = "reports/narrative_packages"):
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
        logger.info(f"Loaded {len(self.fragments)} fragments for package building")

    def _fragment_score(self, frag: dict, emotion: str, conflict: str,
                        relationship: str, genre: str) -> float:
        score = 0.0
        if emotion and frag.get("emotion", "").lower() == emotion.lower():
            score += 0.3
        if conflict and frag.get("conflict_type", "").lower() == conflict.lower():
            score += 0.2
        if relationship and frag.get("relationship_type", "").lower() == relationship.lower():
            score += 0.2
        if genre:
            genre_tags = [t.lower() for t in frag.get("genre_tags", [])]
            if genre.lower() in genre_tags:
                score += 0.15
            hint = frag.get("genre_hint", "").lower()
            if genre.lower() == hint:
                score += 0.1
        score += frag.get("quality_score", 0) * 0.2
        return score

    @staticmethod
    def _get_meta_categories(frag: dict) -> set:
        """Get categories from metadata (for merged fragments)."""
        meta = frag.get("metadata", {})
        if isinstance(meta, dict):
            cats = set(c.lower() for c in meta.get("categories", []))
            subs = set(s.lower() for s in meta.get("subcategories", []))
            return cats | subs
        return set()

    def _filter_by_role(self, category_prefix: str) -> List[dict]:
        candidates = []
        for frag in self.fragments:
            cat = frag.get("category", "").lower()
            sub = frag.get("subcategory", "").lower()
            meta_cats = self._get_meta_categories(frag)
            if cat.startswith(category_prefix) or sub.startswith(category_prefix) \
               or any(c.startswith(category_prefix) for c in meta_cats):
                candidates.append(frag)
        return candidates

    def _matches_group(self, frag: dict, group_name: str, match_terms: tuple) -> bool:
        """Check if fragment matches a group by category, subcategory, or metadata."""
        cat = frag.get("category", "").lower()
        sub = frag.get("subcategory", "").lower()
        if cat == group_name or cat.startswith(f"{group_name}_") or sub == group_name:
            return True
        if sub in match_terms:
            return True
        # Check metadata for merged fragments
        meta_cats = self._get_meta_categories(frag)
        if group_name in meta_cats or any(t in meta_cats for t in match_terms):
            return True
        return False

    def build(self, goal: str, emotion: str = "", conflict: str = "",
              relationship: str = "", genre: str = "",
              fragments_per_group: int = 5) -> NarrativePackage:
        package = NarrativePackage(goal, emotion, conflict, relationship, genre)

        cats = {
            "dialogue": [],
            "actions": [],
            "body_language": [],
            "conflicts": [],
            "memories": [],
            "sensory_details": [],
            "reactions": [],
        }

        group_matchers = {
            "dialogue": ("dialogue_subtext", "dialogue_confessions", "dialogue_arguments",
                         "dialogue_threats", "dialogue_flirtation", "dialogue_negotiation"),
            "actions": ("physical_actions", "goal_driven_actions", "investigation_actions",
                        "combat_actions", "social_actions"),
            "body_language": ("microexpressions", "facial_expressions", "gestures",
                              "movement_patterns"),
            "conflicts": ("internal_conflicts", "interpersonal_conflicts",
                          "group_conflicts", "institutional_conflicts", "moral_conflicts"),
            "memories": ("flashbacks", "trauma_memories", "nostalgic_memories",
                         "regret_memories", "victory_memories"),
            "sensory_details": ("visual", "auditory", "olfactory", "tactile", "gustatory"),
            "reactions": ("emotional_reactions", "physical_reactions", "social_reactions"),
        }

        for frag in self.fragments:
            score = self._fragment_score(frag, emotion, conflict, relationship, genre)
            assigned = False
            for group_name, match_terms in group_matchers.items():
                if self._matches_group(frag, group_name, match_terms):
                    cats[group_name].append((score, frag))
                    assigned = True
                    break
            # If no match, try to infer from narrative_function or scene_role
            if not assigned:
                nf = frag.get("narrative_function", "").lower()
                sr = frag.get("scene_role", "").lower()
                if nf in ("character_development", "emotional_beat"):
                    cats["reactions"].append((score, frag))
                elif frag.get("emotion", ""):
                    cats["memories"].append((score, frag))
                elif nf == "worldbuilding":
                    cats["sensory_details"].append((score, frag))

        for group_name in cats:
            cats[group_name].sort(key=lambda x: -x[0])
            selected = [frag for _, frag in cats[group_name][:fragments_per_group]]
            setattr(package, group_name, selected)

        package.metadata = {
            "total_corpus": len(self.fragments),
            "candidates_by_group": {k: len(v) for k, v in cats.items()},
            "fragments_per_group": fragments_per_group,
        }

        logger.info(f"Built package for goal='{goal}': {package.to_dict()['total_fragments']} fragments")
        return package

    def build_demo_packages(self) -> List[dict]:
        scenarios = [
            {"goal": "angry confrontation", "emotion": "anger", "conflict": "interpersonal",
             "relationship": "", "genre": ""},
            {"goal": "romantic reunion", "emotion": "joy", "conflict": "",
             "relationship": "romances", "genre": "romance"},
            {"goal": "battle scene", "emotion": "fear", "conflict": "group",
             "relationship": "", "genre": "fantasy"},
            {"goal": "mystery investigation", "emotion": "fear", "conflict": "",
             "relationship": "", "genre": "mystery"},
            {"goal": "betrayal and loss", "emotion": "sadness", "conflict": "interpersonal",
             "relationship": "betrayals", "genre": ""},
        ]
        packages = []
        for s in scenarios:
            pkg = self.build(**s)
            pkg_dict = pkg.to_dict()
            packages.append(pkg_dict)

        output_path = self.output_dir / "narrative_packages_demo.json"
        with open(output_path, "w") as f:
            json.dump(packages, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote {len(packages)} demo packages to {output_path}")
        return packages


if __name__ == "__main__":
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "data_pipeline/output/fragments_cleaned.jsonl"
    output = sys.argv[2] if len(sys.argv) > 2 else "reports/narrative_packages"
    builder = NarrativePackageBuilder(source, output)
    builder.build_demo_packages()
