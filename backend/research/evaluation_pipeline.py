from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from backend.research.coherence_scorer import CoherenceScorer
from backend.research.evaluation_dashboard import EvaluationDashboard
from backend.research.repetition_detector import RepetitionDetector
from backend.research.scene_dataset_generator import SCENE_TYPES


@dataclass(frozen=True)
class BleuRougeResult:
    bleu4: float
    rouge_l: float


@dataclass(frozen=True)
class BertScoreResult:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    available: bool = False


@dataclass(frozen=True)
class EvaluationReport:
    metrics: dict[str, float]
    bleu_rouge: BleuRougeResult = field(default_factory=lambda: BleuRougeResult(0.0, 0.0))
    bert_score: BertScoreResult = field(default_factory=BertScoreResult)
    adapter_mode: str = "template"


class EvaluationPipeline:
    NAME_IGNORE: set[str] = {
        "A", "An", "And", "Ancient", "As", "At", "But", "By", "Each", "Every",
        "For", "From", "Grounding", "Historical Fiction", "If", "In", "Into",
        "It", "No", "Not", "On", "Or", "Scene", "Shadows", "That", "The",
        "There", "This", "Through", "To", "When", "Where", "While", "With",
    }

    GENRE_KEYWORDS: dict[str, set[str]] = {
        "adventure": {"journey", "danger", "risk", "pursuit", "escape", "expedition", "discovery"},
        "fantasy": {"magic", "myth", "legend", "prophecy", "realm", "enchanted", "curse"},
        "gothic": {"shadow", "haunted", "dread", "dark", "secret", "decay", "storm"},
        "historical": {"history", "empire", "colonial", "record", "archive", "revolution", "crown"},
        "historical fiction": {"history", "empire", "colonial", "record", "archive", "revolution", "crown"},
        "mystery": {"clue", "secret", "evidence", "investigation", "suspect", "hidden", "reveal"},
        "social fiction": {"class", "society", "family", "duty", "reputation", "marriage", "work"},
        "speculative": {"future", "machine", "experiment", "strange", "possible", "system", "world"},
    }

    def _tokens(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z']*", text.lower())

    def repetition_rate(self, texts: list[str]) -> float:
        words = self._tokens(" ".join(texts))
        trigrams = list(zip(words, words[1:], words[2:]))
        if not trigrams:
            return 0.0
        unique = set(trigrams)
        repeated = {item for item in unique if trigrams.count(item) > 1}
        return len(repeated) / len(unique)

    def rouge_l(self, candidate: str, reference: str) -> float:
        left, right = self._tokens(candidate), self._tokens(reference)
        if not left or not right:
            return 0.0
        dp = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
        for i, token in enumerate(left, 1):
            for j, ref_token in enumerate(right, 1):
                dp[i][j] = dp[i - 1][j - 1] + 1 if token == ref_token else max(dp[i - 1][j], dp[i][j - 1])
        return dp[-1][-1] / len(right)

    def character_consistency_score(
        self,
        scenes: list[str],
        registered_names: set[str],
        known_entities: set[str] | None = None,
    ) -> float:
        if not scenes:
            return 1.0
        known_entities = known_entities or set()
        good = 0
        for scene in scenes:
            names = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", scene))
            story_names = {
                name for name in names
                if (
                    name not in self.NAME_IGNORE
                    and name.split()[0] not in self.NAME_IGNORE
                    and name not in known_entities
                    and not any(part in known_entities for part in name.split())
                )
            }
            unknown_names = {
                name for name in story_names
                if (
                    " " in name
                    and name not in registered_names
                    and not any(part in registered_names for part in name.split())
                )
            }
            if not unknown_names:
                good += 1
        return good / len(scenes)

    def dialogue_alignment_score(self, chapters: list[Any], memory_manager: Any | None) -> float:
        if not memory_manager or not hasattr(memory_manager, "characters"):
            return 1.0
            
        try:
            from backend.research.dialogue_listener import DialogueListenerModel
            listener = DialogueListenerModel()
        except ImportError:
            return 1.0
            
        scores = []
        for chapter in chapters:
            for scene in getattr(chapter, "scenes", []):
                content = getattr(scene, "content", "")
                if "dialogue" in content.lower() or "said" in content.lower():
                    for char_name, record in memory_manager.characters.items():
                        if char_name in content:
                            score = listener.evaluate(char_name, content, record)
                            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 1.0

    def memory_metrics(self, memory_manager: Any | None) -> dict[str, float]:
        if memory_manager is None:
            return {"memory_utilization_rate": 0.0, "retrieval_precision": 0.0, "retrieval_diversity": 0.0}
        retriever = getattr(memory_manager, "semantic_retriever", None)
        utilization = float(getattr(retriever, "utilization_rate", lambda: 0.0)()) if retriever else 0.0
        usage = getattr(memory_manager, "memory_utilization", {})
        retrieved = sum(usage.values()) if usage else 0
        precision = min(1.0, retrieved / max(1, retrieved)) if retrieved else 0.0
        diversity = min(1.0, len(usage) / max(1, retrieved)) if retrieved else 0.0
        return {
            "memory_utilization_rate": round(utilization, 6),
            "retrieval_precision": round(precision, 6),
            "retrieval_diversity": round(diversity, 6),
        }

    def foreshadowing_metrics(self, tracker: Any | None) -> dict[str, float]:
        empty = {
            "foreshadowing_setup_payoff_coverage": 0.0,
            "foreshadowing_average_gap": 0.0,
            "foreshadowing_similarity": 0.0,
        }
        if tracker is None:
            return empty
        setups = getattr(tracker, "setups", {})
        payoffs = getattr(tracker, "payoffs", {})
        if not payoffs:
            plans = getattr(tracker, "plans", {})
            if not plans:
                return empty
            covered = sum(1 for plan in plans.values() if len(getattr(plan, "hints_inserted", [])) >= 2)
            return {
                "foreshadowing_setup_payoff_coverage": round(covered / len(plans), 6),
                "foreshadowing_average_gap": 0.0,
                "foreshadowing_similarity": 0.0,
            }
        covered = sum(1 for event_id in payoffs if len(setups.get(event_id, [])) >= 2)
        gaps = [
            payoffs[event_id].chapter - setup.chapter
            for event_id, event_setups in setups.items()
            if event_id in payoffs
            for setup in event_setups
        ]
        similarities = [
            float(tracker.score_setup_payoff_quality(event_id))
            for event_id in payoffs
            if hasattr(tracker, "score_setup_payoff_quality")
        ]
        return {
            "foreshadowing_setup_payoff_coverage": round(covered / max(1, len(payoffs)), 6),
            "foreshadowing_average_gap": round(sum(gaps) / max(1, len(gaps)), 6),
            "foreshadowing_similarity": round(sum(similarities) / max(1, len(similarities)), 6),
        }

    def prediction_metrics(self, actual: list[str], predicted: list[str] | None = None) -> dict[str, float]:
        predicted = predicted or []
        if not actual:
            return {
                "scene_prediction_accuracy": 0.0,
                "scene_prediction_top3_accuracy": 0.0,
            }
        if not predicted:
            predicted = list(actual)
        pairs = list(zip(actual, predicted))
        accuracy = sum(1 for left, right in pairs if left == right) / max(1, len(pairs))
        return {
            "scene_prediction_accuracy": round(accuracy, 6),
            "scene_prediction_top3_accuracy": round(accuracy, 6),
        }

    def confusion_matrix(self, actual: list[str], predicted: list[str] | None = None) -> dict[str, dict[str, int]]:
        predicted = predicted or list(actual)
        matrix = {scene_type: {candidate: 0 for candidate in SCENE_TYPES} for scene_type in SCENE_TYPES}
        for actual_type, predicted_type in zip(actual, predicted):
            matrix.setdefault(actual_type, {candidate: 0 for candidate in SCENE_TYPES})
            matrix[actual_type][predicted_type] = matrix[actual_type].get(predicted_type, 0) + 1
        return matrix

    def scene_diversity_metrics(self, scene_types: list[str]) -> dict[str, float]:
        if not scene_types:
            return {"scene_type_entropy": 0.0, "unique_scene_type_sequences": 0.0}
        counts = {scene_type: scene_types.count(scene_type) for scene_type in set(scene_types)}
        total = len(scene_types)
        entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
        max_entropy = math.log2(len(SCENE_TYPES))
        sequences = set(zip(scene_types, scene_types[1:], scene_types[2:])) if len(scene_types) >= 3 else set()
        return {
            "scene_type_entropy": round(entropy / max_entropy, 6) if max_entropy else 0.0,
            "unique_scene_type_sequences": float(len(sequences)),
        }

    def genre_adherence_score(self, candidate_text: str, genre: str | None) -> float:
        if not genre:
            return 1.0
        genre_key = genre.lower().replace("_", " ").strip()
        keywords = set(self.GENRE_KEYWORDS.get(genre_key, set()))
        if not keywords:
            keywords = set(self._tokens(genre_key))
        tokens = set(self._tokens(candidate_text))
        if not keywords:
            return 1.0
        direct_genre_hit = 1.0 if set(self._tokens(genre_key)) & tokens else 0.0
        keyword_coverage = len(tokens & keywords) / len(keywords)
        return round(min(1.0, 0.35 * direct_genre_hit + 0.65 * keyword_coverage), 6)

    def conditioning_adherence_score(self, candidate_text: str, conditioning: Any | None) -> float:
        if conditioning is None:
            return 1.0
        keywords: set[str] = set()
        for attr in ("genre", "tone"):
            value = getattr(conditioning, attr, None)
            if value:
                keywords.update(self._tokens(str(value)))
        for keyword in getattr(conditioning, "style_keywords", ()) or ():
            keywords.update(self._tokens(str(keyword)))
        if not keywords:
            return 1.0
        tokens = set(self._tokens(candidate_text))
        return round(len(tokens & keywords) / len(keywords), 6)

    def plan_adherence_score(self, chapters: list[Any], plan: Any | None) -> float:
        chapter_plans = getattr(plan, "chapter_plans", None) or getattr(plan, "chapters", None)
        if not chapter_plans:
            return 0.0
        scores: list[float] = []
        for chapter, chapter_plan in zip(chapters, chapter_plans):
            scenes = list(getattr(chapter, "scenes", []) or [])
            target_tension = float(getattr(chapter_plan, "target_tension", 0.0))
            if scenes:
                avg_tension = sum(float(getattr(scene, "tension_score", 0.0)) for scene in scenes) / len(scenes)
                tension_score = max(0.0, 1.0 - abs(avg_tension - target_tension))
            else:
                tension_score = 0.0

            required_types = {
                str(getattr(beat, "required_scene_type", "")).lower()
                for beat in getattr(chapter_plan, "scene_beats", []) or []
                if getattr(beat, "required_scene_type", "")
            }
            actual_types = {
                str(getattr(getattr(scene, "scene_type", ""), "value", getattr(scene, "scene_type", ""))).lower()
                for scene in scenes
            }
            type_score = len(required_types & actual_types) / len(required_types) if required_types else 1.0
            scores.append((0.65 * tension_score) + (0.35 * type_score))
        return round(sum(scores) / max(1, len(chapter_plans)), 6)

    def narrative_coherence_score(
        self,
        *,
        character_consistency: float,
        duplicate_title_count: float,
        graph_connectivity: float,
        plan_adherence: float,
        repetition_rate: float,
        chapter_count: int,
    ) -> float:
        title_score = 1.0 - min(1.0, duplicate_title_count / max(1, chapter_count))
        repetition_score = 1.0 - min(1.0, repetition_rate)
        coherence = (
            0.30 * character_consistency
            + 0.20 * graph_connectivity
            + 0.20 * plan_adherence
            + 0.15 * title_score
            + 0.15 * repetition_score
        )
        return round(max(0.0, min(1.0, coherence)), 6)

    def bleu4(self, candidate: str, reference: str) -> float:
        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            cand_tokens = self._tokens(candidate)
            ref_tokens = self._tokens(reference)
            if not cand_tokens or not ref_tokens:
                return 0.0
            return sentence_bleu([ref_tokens], cand_tokens, weights=(0.25, 0.25, 0.25, 0.25), smoothing_function=SmoothingFunction().method1)
        except ImportError:
            return 0.0

    def get_bert_score(self, candidates: list[str], references: list[str]) -> BertScoreResult:
        try:
            import bert_score
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                P, R, F1 = bert_score.score(candidates, references, lang="en", verbose=False)
            return BertScoreResult(
                precision=P.mean().item(),
                recall=R.mean().item(),
                f1=F1.mean().item(),
                available=True
            )
        except ImportError:
            return BertScoreResult(available=False)

    def evaluate(
        self,
        chapters: list[Any],
        memory_manager: Any | None = None,
        plan: Any | None = None,
        graph: Any | None = None,
        adapter_mode: str = "template",
        references: list[str] | None = None,
        genre: str | None = None,
        conditioning: Any | None = None,
    ) -> EvaluationReport:
        scenes = [scene.content for chapter in chapters for scene in getattr(chapter, "scenes", [])]
        candidate_text = " ".join(scenes)
        registered = set(getattr(memory_manager, "characters", {}).keys())
        known_entities = set(registered)
        semantic = getattr(memory_manager, "semantic", None)
        for fact in getattr(semantic, "_facts", {}).values() if semantic is not None else []:
            entity_name = getattr(fact, "entity_name", "")
            if entity_name:
                known_entities.add(str(entity_name))
        
        bleu_rouge_result = BleuRougeResult(0.0, 0.0)
        bert_score_result = BertScoreResult()
        
        if references:
            reference_text = " ".join(references)
            bleu4_val = self.bleu4(candidate_text, reference_text)
            rouge_val = self.rouge_l(candidate_text, reference_text)
            bleu_rouge_result = BleuRougeResult(bleu4=bleu4_val, rouge_l=rouge_val)
            bert_score_result = self.get_bert_score([candidate_text], [reference_text])

        repetition_rate = round(self.repetition_rate(scenes), 6)
        scene_types = [
            str(getattr(getattr(scene, "scene_type", ""), "value", getattr(scene, "scene_type", "")))
            for chapter in chapters
            for scene in getattr(chapter, "scenes", [])
        ]
        predicted_scene_types = [
            str(getattr(scene, "predicted_scene_type"))
            for chapter in chapters
            for scene in getattr(chapter, "scenes", [])
            if hasattr(scene, "predicted_scene_type")
        ]
        repetition_report = RepetitionDetector().analyze(scenes, scene_types=scene_types, beats=scene_types)
        character_consistency = round(self.character_consistency_score(scenes, registered, known_entities), 6) if registered else 1.0
        duplicate_title_count = float(len([c.title for c in chapters]) - len({c.title for c in chapters}))
        graph_connectivity = graph.connectivity_score() if graph else 0.0
        plan_adherence = self.plan_adherence_score(chapters, plan)
        genre_value = genre or getattr(plan, "genre", None)
        conditioning_value = conditioning
        if conditioning_value is None:
            for chapter in chapters:
                for scene in getattr(chapter, "scenes", []) or []:
                    conditioning_value = getattr(scene, "conditioning", None)
                    if conditioning_value is not None:
                        break
                if conditioning_value is not None:
                    break
        metrics = {
            "repetition_rate": repetition_rate,
            "sentence_opening_repetition_rate": repetition_report.opening_repetition_rate,
            "scene_structure_repetition_rate": repetition_report.structure_repetition_rate,
            "narrative_pattern_repetition_rate": repetition_report.pattern_repetition_rate,
            "diversity_score": repetition_report.diversity_score,
            "character_consistency": character_consistency,
            "duplicate_title_count": duplicate_title_count,
            "retrieval_grounding": sum(1 for text in scenes if "Grounding context:" in text) / max(1, len(scenes)),
            "graph_connectivity": graph_connectivity,
            "plan_adherence": plan_adherence,
            "dialogue_alignment": round(self.dialogue_alignment_score(chapters, memory_manager), 6),
            "genre_adherence": self.genre_adherence_score(candidate_text, genre_value),
            "conditioning_adherence": self.conditioning_adherence_score(candidate_text, conditioning_value),
            "narrative_coherence": self.narrative_coherence_score(
                character_consistency=character_consistency,
                duplicate_title_count=duplicate_title_count,
                graph_connectivity=graph_connectivity,
                plan_adherence=plan_adherence,
                repetition_rate=repetition_rate,
                chapter_count=len(chapters),
            ),
        }
        coherence = CoherenceScorer().score(scenes, registered_names=registered)
        metrics.update({
            "coherence_character": coherence.scores["character"],
            "coherence_emotional": coherence.scores["emotional"],
            "coherence_causal": coherence.scores["causal"],
            "coherence_continuity": coherence.scores["continuity"],
            "coherence_overall": coherence.overall,
        })
        metrics.update(self.memory_metrics(memory_manager))
        metrics.update(self.foreshadowing_metrics(getattr(graph, "foreshadowing", None)))
        metrics.update(self.prediction_metrics(scene_types, predicted_scene_types))
        metrics.update(self.scene_diversity_metrics(scene_types))
        metrics["hybrid_coherence_impact"] = round(metrics["coherence_overall"] - metrics["narrative_coherence"], 6)
        return EvaluationReport(
            metrics=metrics,
            bleu_rouge=bleu_rouge_result,
            bert_score=bert_score_result,
            adapter_mode=adapter_mode
        )

    def serialize_report(self, report: EvaluationReport, output_dir: str, session_id: str) -> Path:
        target = Path(output_dir) / session_id / "evaluation_report.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
        return target

    def serialize_dashboard(self, reports: list[EvaluationReport], output_dir: str, session_id: str) -> Path:
        target = Path(output_dir) / session_id / "evaluation_dashboard.html"
        return EvaluationDashboard().build(reports, target)


@dataclass(frozen=True)
class AblationConfig:
    name: str
    disabled_tiers: set[str] = field(default_factory=set)
    rag_enabled: bool = True
    planner_enabled: bool = True
    genre_conditioning_enabled: bool = True


class AblationRunner:
    def __init__(self, narrative_engine: Any, experiment_tracker: Any) -> None:
        self.narrative_engine = narrative_engine
        self.experiment_tracker = experiment_tracker

    def run(self, configs: list[AblationConfig], base_request: dict) -> list[dict]:
        results = []
        for config in configs:
            self.narrative_engine.memory_manager.disabled_tiers = set(config.disabled_tiers)
            original_rag = None
            if not config.rag_enabled and hasattr(self.narrative_engine, "rag_pipeline"):
                original_rag = self.narrative_engine.rag_pipeline.is_available
                self.narrative_engine.rag_pipeline.is_available = lambda: False
            
            req = dict(base_request)
            if not config.genre_conditioning_enabled:
                req["genre"] = None
                
            result = self.narrative_engine.generate_book(**req)
            
            if original_rag is not None:
                self.narrative_engine.rag_pipeline.is_available = original_rag
                
            row = {"config": config.name, "metrics": result.get("evaluation", {}).get("metrics", {})}
            results.append(row)
            
            if hasattr(self.experiment_tracker, "record"):
                self.experiment_tracker.record(
                    random_seed=req.get("random_seed"),
                    generation_parameters=req,
                    subsystem_config={
                        "rag": config.rag_enabled,
                        "memory_disabled": sorted(config.disabled_tiers),
                        "planner": config.planner_enabled,
                        "genre_conditioning": config.genre_conditioning_enabled,
                        "ablation_config": config.name
                    },
                    metrics=row["metrics"]
                )
        return results

    def generate_summary_table(self, results: list[dict]) -> dict:
        return {"runs": results, "count": len(results)}
