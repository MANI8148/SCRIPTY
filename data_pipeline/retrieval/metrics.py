"""
Retrieval Metrics — compute Precision/Recall, emotion/conflict/relationship/
dialogue-intent/scene-function match rates, narrative relevance, diversity.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DIALOGUE_INTENTS = {"threat", "persuasion", "confession", "warning", "question",
                    "command", "comfort", "deception", "bargain", "flirtation"}
SCENE_FUNCTIONS = {"opening", "rising_action", "climax", "falling_action",
                   "resolution", "turning_point", "flashback", "setup", "payoff"}


class RetrievalMetrics:
    def __init__(self, results: List[Tuple[str, float]], query: dict,
                 corpus_map: Dict[str, dict]):
        self.results = results
        self.query = query
        self.corpus_map = corpus_map
        self.q_cat = query.get("category", "").lower()
        self.q_sub = query.get("subcategory", "").lower()
        self.q_emotion = query.get("emotion", "").lower()
        self.q_expected = set(f.lower() for f in query.get("expected_features", []))

    def relevant_ids(self, top_k: int) -> List[str]:
        return [rid for rid, _ in self.results[:top_k]]

    def _is_relevant(self, frag: dict) -> bool:
        if frag.get("_cat_lower", "") == self.q_cat \
           or frag.get("_sub_lower", "") == self.q_sub:
            return True
        if self.q_emotion and frag.get("_emo_lower", "") == self.q_emotion:
            return True
        if self.q_expected and (self.q_expected & frag.get("_tags_set", set())):
            return True
        return False

    def precision_at_k(self, k: int) -> float:
        retrieved = self.relevant_ids(k)
        if not retrieved:
            return 0.0
        relevant = sum(1 for rid in retrieved if rid in self.corpus_map
                       and self._is_relevant(self.corpus_map[rid]))
        return relevant / k

    def recall_at_k(self, k: int, total_relevant: Optional[int] = None) -> float:
        retrieved = self.relevant_ids(k)
        if total_relevant is None:
            if not hasattr(self, "_total_relevant"):
                self._total_relevant = sum(1 for f in self.corpus_map.values()
                                           if self._is_relevant(f))
            total_relevant = self._total_relevant
        if total_relevant == 0:
            return 0.0
        relevant = sum(1 for rid in retrieved if rid in self.corpus_map
                       and self._is_relevant(self.corpus_map[rid]))
        return relevant / total_relevant

    def emotion_match_rate(self) -> float:
        if not self.q_emotion:
            return 0.0
        retrieved = self.relevant_ids(20)
        matches = sum(1 for rid in retrieved if rid in self.corpus_map
                      and self.corpus_map[rid].get("emotion", "").lower() == self.q_emotion)
        return matches / max(1, len(retrieved))

    def conflict_match_rate(self) -> float:
        q_conflict = self.q_sub if "conflict" in self.q_sub else ""
        if not q_conflict:
            return 0.0
        retrieved = self.relevant_ids(20)
        matches = sum(1 for rid in retrieved if rid in self.corpus_map
                      and self.corpus_map[rid].get("conflict_type", "").lower() == q_conflict)
        return matches / max(1, len(retrieved))

    def relationship_match_rate(self) -> float:
        q_rel = self.q_sub if self.q_sub in {"friendships", "rivalries", "romances",
                                              "family_relationships", "mentor_relationships",
                                              "betrayals"} else ""
        if not q_rel:
            return 0.0
        retrieved = self.relevant_ids(20)
        matches = sum(1 for rid in retrieved if rid in self.corpus_map
                      and self.corpus_map[rid].get("relationship_type", "").lower() == q_rel)
        return matches / max(1, len(retrieved))

    def dialogue_intent_match_rate(self, intent: Optional[str] = None) -> float:
        target = intent or self.q_sub
        if target not in DIALOGUE_INTENTS:
            return 0.0
        retrieved = self.relevant_ids(20)
        matches = sum(1 for rid in retrieved if rid in self.corpus_map
                      and self._has_dialogue_intent(self.corpus_map[rid], target))
        return matches / max(1, len(retrieved))

    def scene_function_match_rate(self, func: Optional[str] = None) -> float:
        target = func or self.q_sub
        if target not in SCENE_FUNCTIONS:
            return 0.0
        retrieved = self.relevant_ids(20)
        matches = sum(1 for rid in retrieved if rid in self.corpus_map
                      and self.corpus_map[rid].get("scene_role", "").lower() == target)
        return matches / max(1, len(retrieved))

    def narrative_relevance(self) -> float:
        if not self.q_expected:
            return 0.0
        retrieved = self.relevant_ids(20)
        if not retrieved:
            return 0.0
        feature_hits = Counter()
        for rid in retrieved:
            frag = self.corpus_map.get(rid, {})
            f_cat = frag.get("_cat_lower", "")
            f_sub = frag.get("_sub_lower", "")
            f_tags = frag.get("_tags_set", set())
            for feat in self.q_expected:
                if feat == f_cat or feat == f_sub or feat in f_tags:
                    feature_hits[feat] += 1
        return sum(feature_hits.values()) / (len(self.q_expected) * max(1, len(retrieved)))

    def retrieval_diversity(self) -> float:
        retrieved = self.relevant_ids(20)
        if not retrieved:
            return 0.0
        cats = set()
        for rid in retrieved:
            frag = self.corpus_map.get(rid, {})
            cats.add(frag.get("category", "unknown"))
            cats.add(frag.get("subcategory", "unknown"))
        return len(cats) / max(1, len(retrieved))

    def reusability_score(self) -> float:
        retrieved = self.relevant_ids(20)
        if not retrieved:
            return 0.0
        scores = []
        for rid in retrieved:
            frag = self.corpus_map.get(rid, {})
            qs = frag.get("quality_score", 0)
            tl = frag.get("tension", 0)
            sk = frag.get("stakes", 0)
            ei = frag.get("emotion_intensity", 0)
            scores.append((qs + tl + sk + ei) / 4.0)
        return sum(scores) / max(1, len(scores))

    def all_metrics(self) -> dict:
        return {
            "precision_at_5": self.precision_at_k(5),
            "precision_at_10": self.precision_at_k(10),
            "recall_at_10": self.recall_at_k(10),
            "recall_at_20": self.recall_at_k(20),
            "emotion_match_rate": self.emotion_match_rate(),
            "conflict_match_rate": self.conflict_match_rate(),
            "relationship_match_rate": self.relationship_match_rate(),
            "dialogue_intent_match_rate": self.dialogue_intent_match_rate(),
            "scene_function_match_rate": self.scene_function_match_rate(),
            "narrative_relevance": self.narrative_relevance(),
            "retrieval_diversity": self.retrieval_diversity(),
            "reusability_score": self.reusability_score(),
        }

    @staticmethod
    def _has_dialogue_intent(frag: dict, intent: str) -> bool:
        cat = frag.get("category", "").lower()
        sub = frag.get("subcategory", "").lower()
        intent_keywords = {
            "threat":       {"threat", "warning", "or else", "will regret", "better not"},
            "persuasion":   {"convince", "persuade", "you should", "just think", "consider"},
            "confession":   {"confess", "admit", "truth is", "i lied", "i was the one"},
            "warning":      {"beware", "caution", "danger", "don't", "stop", "careful"},
            "question":     {"?", "ask", "who", "what", "when", "where", "why", "how", "did you"},
            "command":      {"do it", "listen", "stop", "go", "come", "tell me", "give me"},
            "comfort":      {"there there", "it's okay", "you'll be fine", "shh", "i'm here"},
            "deception":    {"lie", "deceive", "not true", "never happened", "i swear"},
            "bargain":      {"deal", "trade", "offer", "if you", "in exchange", "consider this"},
            "flirtation":   {"beautiful", "handsome", "charming", "you look", "flirt"},
        }
        if cat == "dialogue" and sub == f"dialogue_{intent}":
            return True
        text = frag.get("text", "").lower()
        keywords = intent_keywords.get(intent, set())
        return any(kw in text for kw in keywords)
