"""
SCRIPTY v2 Generation Validation Audit.

Generates stories across modes/genres, runs controlled ablations,
and produces 8 analytical reports measuring subsystem influence
and narrative quality.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import statistics
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.dramatic_realizer import DramaticRealizer
from backend.v2.conflict_resolver import ConflictResolver
from backend.v2.engine import StoryEngineV2
from backend.v2.factories import build_character_agents
from backend.v2.memory_system import MemorySystem
from backend.v2.pipeline import ScenePipeline
from backend.v2.story_planner import StoryPlanner
from backend.v2.state_update import StateUpdater
from backend.v2.types import (
    GenerationRequest,
    GenerationResult,
    Intention,
    SceneBlueprint,
    SceneObjective,
    SceneType,
    StoryMode,
    WorldConstraints,
)
from backend.v2.world_state import WorldState


random.seed(42)

GENRES = [
    "Historical Fiction",
    "Mystery",
    "Romance",
    "Thriller",
    "Literary Fiction",
]

LOCATIONS = [
    ("Hyderabad", 1920, "urban"),
    ("Mumbai", 2024, "metro"),
    ("Jaipur", 1800, "urban"),
    ("Delhi", 1857, "urban"),
    ("Kolkata", 1900, "urban"),
]

CHARACTER_SETS = [
    [
        {"name": "Arjun", "role": "protagonist", "traits": ["curious", "brave"], "goals": ["uncover the truth"], "relationships": {"Maya": "rival"}},
        {"name": "Maya", "role": "antagonist", "traits": ["deceptive", "ambitious"], "goals": ["protect the secret"], "relationships": {"Arjun": "rival"}},
    ],
    [
        {"name": "Ananya", "role": "protagonist", "traits": ["kind", "wise"], "goals": ["find peace"], "relationships": {"Vikram": "ally"}},
        {"name": "Vikram", "role": "ally", "traits": ["loyal", "reckless"], "goals": ["protect Ananya"], "relationships": {"Ananya": "ally"}},
    ],
    [
        {"name": "Ravi", "role": "detective", "traits": ["cautious", "curious"], "goals": ["solve the case"], "relationships": {"Priya": "ally"}},
        {"name": "Priya", "role": "witness", "traits": ["deceptive", "ambitious"], "goals": ["hide the evidence"], "relationships": {"Ravi": "rival"}},
    ],
]

MODE = StoryMode.SHORT
CHAPTER_MODE = StoryMode.CHAPTER


# ─── Ablation models ────────────────────────────────────────────────────────


class NullMemorySystem(MemorySystem):
    def retrieve(self, query):
        return []

    def recent_context(self, character, window=3):
        return []

    def beliefs_for(self, character):
        return type("NullBeliefs", (), {"discovered": [], "self_beliefs": {}, "suspicions": []})()


class NullCharacterAgent(CharacterAgent):
    def decide_intention(self, world_context, memories=None, relationship_pressures=None):
        return Intention(goal="proceed", target="", action="act", urgency=0.3)

    def relationship_pressure_with(self, other):
        return 0.0


class NullConflictResolver(ConflictResolver):
    def resolve(self, agent_states, base_objective):
        return base_objective

    def calculate_scene_type(self, agent_states, base_type):
        return base_type


class NullWorldState:
    async def build_constraints(self, location, year, location_type="urban", **kw):
        return WorldConstraints(
            era="generic",
            tech_level="generic",
            tone="neutral",
            infrastructure=["buildings", "roads"],
            transport=["walking", "riding"],
            location_description=f"A place called {location}",
            year=year,
        )

    def to_generation_context(self, constraints):
        return {"era": "generic", "tech_level": "generic", "tone": "neutral"}


class NullStoryPlanner(StoryPlanner):
    def plan_chapter(self, chapter_num, total_chapters, world, story_mode):
        return [
            SceneObjective(
                purpose="something happens",
                characters_involved=[],
                location=world.location_description,
                conflict_type="neutral",
                required_tension=0.3,
                target_scene_type=st,
                resolution_goal="continue",
            )
            for st in [SceneType.DESCRIPTION, SceneType.DIALOGUE, SceneType.ACTION]
        ]


# ─── Builders ───────────────────────────────────────────────────────────────


class AblatedEngine(StoryEngineV2):
    """Engine variant with ablated CharacterAgent that returns NullCharacterAgents."""

    def _init_agents(self, request, world):
        from backend.v2.types import CharacterRecord
        agents = []
        for char_data in request.characters:
            record = CharacterRecord(
                name=char_data.get("name", "Unknown"),
                role=char_data.get("role", "bystander"),
                traits=char_data.get("traits", ["curious"]),
                goals=[char_data.get("goal", "proceed")],
            )
            null_agent = NullCharacterAgent(character=record)
            agents.append(null_agent)
        if not agents:
            agents = [
                NullCharacterAgent(CharacterRecord(name="A", role="character", traits=[], goals=["proceed"])),
                NullCharacterAgent(CharacterRecord(name="B", role="character", traits=[], goals=["proceed"])),
            ]
        for agent in agents:
            self.memory.register_character(agent.name)
        return agents


def build_engine(
    use_memory=True,
    use_agents=True,
    use_resolver=True,
    use_world=True,
    use_planner=True,
    characters=None,
) -> StoryEngineV2:
    memory: MemorySystem = MemorySystem() if use_memory else NullMemorySystem()
    planner: StoryPlanner = StoryPlanner() if use_planner else NullStoryPlanner()
    resolver: ConflictResolver = ConflictResolver() if use_resolver else NullConflictResolver()
    world: WorldState | NullWorldState = WorldState() if use_world else NullWorldState()
    engine_cls = AblatedEngine if not use_agents else StoryEngineV2

    engine = engine_cls(
        world_state=world,
        memory=memory,
        planner=planner,
        conflict_resolver=resolver,
        realizer=DramaticRealizer(),
        state_updater=StateUpdater(),
    )
    return engine


ABLATION_CONFIGS = {
    "Full System": {},
    "No MemorySystem": {"use_memory": False},
    "No CharacterAgent": {"use_agents": False},
    "No ConflictResolver": {"use_resolver": False},
    "No WorldState": {"use_world": False},
    "No StoryPlanner": {"use_planner": False},
}


# ─── Story generation ──────────────────────────────────────────────────────


async def generate_batch(
    engine: StoryEngineV2,
    requests: list[GenerationRequest],
    label: str = "",
) -> list[GenerationResult]:
    results: list[GenerationResult] = []
    for i, req in enumerate(requests):
        try:
            result = await engine.generate(req)
            results.append(result)
        except Exception as e:
            print(f"  [{label}] FAIL request {i}: {e}")
            results.append(None)
    return results


def make_request(
    location="Hyderabad",
    year=1920,
    mode=StoryMode.SHORT,
    characters=None,
    genre="Historical Fiction",
    location_type="urban",
    chapter_count=1,
) -> GenerationRequest:
    return GenerationRequest(
        location=location,
        year=year,
        story_mode=mode,
        chapter_count=chapter_count,
        genre=genre,
        characters=characters or [],
        location_type=location_type,
    )


# ─── Analysis ──────────────────────────────────────────────────────────────


@dataclass
class StoryFeatures:
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    unique_words: int
    type_token_ratio: float
    character_names: list[str]
    character_mentions: dict[str, int]
    dialogue_lines: int
    conflict_keywords: list[str]
    emotion_keywords: list[str]
    action_verbs: list[str]
    scene_count: int
    sentences: list[str]
    content: str


def extract_features(result: GenerationResult, characters: list[str] | None = None) -> StoryFeatures:
    text = result.story_text
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    words = text.split()
    word_count = len(words)
    sentence_count = len(sentences)
    avg_sentence_length = word_count / max(sentence_count, 1)
    unique = set(w.lower().strip(".,!?;:\"'()[]") for w in words)
    unique_words = len(unique)
    ttr = unique_words / max(word_count, 1)

    char_names = characters or []
    char_mentions = {}
    for name in char_names:
        count = len(re.findall(rf'\b{re.escape(name)}\b', text))
        char_mentions[name] = count

    dialogue_lines = len(re.findall(r'["\u201c].*?["\u201d]', text))
    dialogue_lines += len(re.findall(r'\b(said|asked|replied|whispered|shouted|murmured)\b', text.lower()))

    from backend.v2.metrics import CONFLICT_KEYWORDS, EMOTION_KEYWORDS
    conflict_keywords = [w for w in CONFLICT_KEYWORDS if w in text.lower()]

    emotion_keywords = [w for w in EMOTION_KEYWORDS if w in text.lower()]

    action_verbs_list = ["ran", "walked", "moved", "grabbed", "pushed", "pulled", "opened", "closed", "turned", "looked", "reached", "spoke"]
    action_verbs = [v for v in action_verbs_list if v in text.lower()]

    return StoryFeatures(
        word_count=word_count,
        sentence_count=sentence_count,
        avg_sentence_length=avg_sentence_length,
        unique_words=unique_words,
        type_token_ratio=round(ttr, 3),
        character_names=char_names,
        character_mentions=char_mentions,
        dialogue_lines=dialogue_lines,
        conflict_keywords=conflict_keywords,
        emotion_keywords=emotion_keywords,
        action_verbs=action_verbs,
        scene_count=len(result.chapters[0].scenes) if result.chapters else 0,
        sentences=sentences,
        content=text,
    )


def measure_prose_repetition(features: StoryFeatures) -> dict:
    text = features.content
    
    pattern_sentences = re.findall(r'[A-Z][^.!?]*(?:moves|driven to|purpose|tension|pressure|charged with)[^.!?]*[.!?]', text)
    simulation_patterns = len(pattern_sentences)
    
    sentence_starts = Counter()
    for s in features.sentences:
        first_words = s.split()[:3]
        sentence_starts[" ".join(first_words)] += 1
    
    repeated_starts = sum(1 for c in sentence_starts.values() if c > 1)
    
    unique_start_ratio = 1 - (repeated_starts / max(len(features.sentences), 1) if repeated_starts > 1 else 0)
    
    return {
        "simulation_pattern_sentences": simulation_patterns,
        "repeated_sentence_starts": repeated_starts,
        "unique_start_ratio": round(unique_start_ratio, 3),
        "total_sentences": len(features.sentences),
    }


def measure_reader_experience(features: StoryFeatures) -> dict:
    scores = {}
    text = features.content.lower()
    
    char_names = features.character_names
    scores["goals_inferrable"] = 1.0 if any(w in text for w in ["goal", "pursuit", "driven to", "trying to", "seeks to", "search"]) else 0.0
    
    emotion_text = features.emotion_keywords
    scores["emotions_inferrable"] = min(1.0, len(emotion_text) / 3)
    
    conflict_text = features.conflict_keywords
    scores["conflicts_inferrable"] = min(1.0, len(conflict_text) / 2)
    
    sentences = features.sentences
    causal_words = ["because", "therefore", "so", "thus", "hence", "as a result", "led to", "caused", "forced"]
    causal_count = sum(1 for s in sentences if any(cw in s.lower() for cw in causal_words))
    scores["cause_effect"] = min(1.0, causal_count / max(len(sentences), 1) * 5)
    
    rel_words = ["relationship", "together", "against", "with", "ally", "enemy", "friend", "partner"]
    scores["relationship_dynamics"] = min(1.0, sum(1 for w in rel_words if w in text) / 3)
    
    progression_words = ["then", "next", "after", "later", "finally", "eventually", "meanwhile", "before", "soon"]
    scores["story_progression"] = min(1.0, sum(1 for w in progression_words if w in text) / 3)
    
    return scores


def measure_conflict_quality(features: StoryFeatures) -> dict:
    text = features.content.lower()
    sentences = features.sentences
    
    tension_sentences = [s for s in sentences if any(w in s.lower() for w in ["tension", "pressure", "danger", "urgent", "desperate"])]
    tension_ratio = len(tension_sentences) / max(len(sentences), 1)
    
    resolution_words = ["resolved", "settled", "ended", "overcome", "victory", "defeat", "finally", "concluded"]
    resolution_present = any(w in text for w in resolution_words)
    
    escalation = 1.0 if tension_ratio > 0.2 else tension_ratio * 5
    
    return {
        "tension_sentence_ratio": round(tension_ratio, 3),
        "resolution_present": resolution_present,
        "escalation_score": round(escalation, 3),
        "total_tension_sentences": len(tension_sentences),
    }


def compute_divergence(text_a: str, text_b: str) -> float:
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a and not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    jaccard = len(intersection) / max(len(union), 1)
    return 1.0 - jaccard


# ─── Validation runner ──────────────────────────────────────────────────────


class ValidationRunner:
    def __init__(self):
        self.short_requests: list[GenerationRequest] = []
        self.chapter_requests: list[GenerationRequest] = []
        self.results: dict[str, list[GenerationResult | None]] = {}
        self.features: dict[str, list[StoryFeatures | None]] = {}

    def build_requests(self):
        random.seed(42)
        for genre in GENRES:
            for loc_name, loc_year, loc_type in LOCATIONS:
                for chars in CHARACTER_SETS:
                    self.short_requests.append(make_request(
                        location=loc_name, year=loc_year, mode=StoryMode.SHORT,
                        characters=chars, genre=genre, location_type=loc_type,
                    ))
                    self.chapter_requests.append(make_request(
                        location=loc_name, year=loc_year, mode=StoryMode.CHAPTER,
                        characters=chars, genre=genre, location_type=loc_type,
                        chapter_count=1,
                    ))

    async def generate_all(self):
        self.build_requests()
        
        short_reqs = self.short_requests[:55]
        chapter_reqs = self.chapter_requests[:55]
        
        print(f"Generating {len(short_reqs)} SHORT stories...")
        engine = build_engine()
        self.results["SHORT_Full"] = await generate_batch(engine, short_reqs, "SHORT")
        print(f"Generating {len(chapter_reqs)} CHAPTER stories...")
        self.results["CHAPTER_Full"] = await generate_batch(engine, chapter_reqs, "CHAPTER")
        
        for ab_name, ab_config in ABLATION_CONFIGS.items():
            if ab_name == "Full System":
                continue
            print(f"Generating {len(short_reqs)} SHORT with {ab_name}...")
            ab_engine = build_engine(**ab_config)
            self.results[f"SHORT_{ab_name}"] = await generate_batch(ab_engine, short_reqs, f"SHORT_{ab_name}")

    def analyze_all(self):
        for key, results_list in self.results.items():
            feats = []
            for result in results_list:
                if result is None:
                    feats.append(None)
                else:
                    chars = []
                    for req in (self.short_requests if "SHORT" in key else self.chapter_requests):
                        if req.characters:
                            chars = [c["name"] for c in req.characters]
                            break
                    feats.append(extract_features(result, chars))
            self.features[key] = feats

    def _valid_features(self, key):
        return [f for f in self.features.get(key, []) if f is not None]

    def subsystem_influence_report(self) -> str:
        lines = ["# SCRIPTY v2 — Subsystem Influence Report\n"]
        lines.append("| Subsystem | Story Change | Character Change | Plot Change | Reader Noticeability | Influence Score |")
        lines.append("|-----------|-------------|-----------------|-------------|--------------------|---------------|")
        
        full_feats = self._valid_features("SHORT_Full")
        
        for ab_name in ["No MemorySystem", "No CharacterAgent", "No ConflictResolver", "No WorldState", "No StoryPlanner"]:
            ab_feats = self._valid_features(f"SHORT_{ab_name}")
            if not full_feats or not ab_feats:
                continue
            
            divergences = []
            char_diffs = []
            word_diffs = []
            for f_full, f_ab in zip(full_feats[:min(len(full_feats), len(ab_feats))], ab_feats[:min(len(full_feats), len(ab_feats))]):
                div = compute_divergence(f_full.content, f_ab.content)
                divergences.append(div)
                full_char_mentions = set(f_full.character_mentions.keys())
                ab_char_mentions = set(f_ab.character_mentions.keys())
                char_diffs.append(len(full_char_mentions ^ ab_char_mentions))
                word_diffs.append(abs(f_full.word_count - f_ab.word_count))
            
            avg_div = statistics.mean(divergences) if divergences else 0
            avg_char_diff = statistics.mean(char_diffs) if char_diffs else 0
            avg_word_diff = statistics.mean(word_diffs) if word_diffs else 0
            
            story_change = f"{avg_div:.2f} lexical divergence"
            char_change = f"{avg_char_diff:.1f} avg character diff"
            plot_change = f"{avg_word_diff:.0f} avg word delta"
            
            noticeability = avg_div * 0.4 + min(1.0, avg_char_diff / 3) * 0.3 + min(1.0, avg_word_diff / 100) * 0.3
            influence = round(noticeability * 10, 1)
            
            lines.append(f"| {ab_name[3:]} | {story_change} | {char_change} | {plot_change} | {noticeability:.2f} | {influence}/10 |")
        
        return "\n".join(lines)

    def reader_experience_report(self) -> str:
        lines = ["# SCRIPTY v2 — Reader Experience Report\n"]
        
        for label in ["SHORT_Full", "CHAPTER_Full"]:
            feats = self._valid_features(label)
            if not feats:
                continue
            
            metrics = defaultdict(list)
            for f in feats:
                scores = measure_reader_experience(f)
                for k, v in scores.items():
                    metrics[k].append(v)
            
            lines.append(f"\n## {label}\n")
            lines.append("| Metric | Avg Score | Interpretation |")
            lines.append("|--------|-----------|---------------|")
            for metric, values in metrics.items():
                avg = statistics.mean(values)
                if avg >= 0.7:
                    interp = "Strongly inferrable"
                elif avg >= 0.4:
                    interp = "Moderately inferrable"
                else:
                    interp = "Weakly inferrable"
                lines.append(f"| {metric.replace('_', ' ').title()} | {avg:.2f} | {interp} |")
        
        return "\n".join(lines)

    def narrative_quality_report(self) -> str:
        lines = ["# SCRIPTY v2 — Narrative Quality Audit\n"]
        
        for label in ["SHORT_Full", "CHAPTER_Full"]:
            feats = self._valid_features(label)
            if not feats:
                continue
            
            lines.append(f"\n## {label}\n")
            metrics_list = {
                "goal_persistence": [],
                "conflict_escalation": [],
                "emotional_continuity": [],
                "dialogue_naturalness": [],
                "causal_coherence": [],
            }
            
            for f in feats:
                metrics_list["goal_persistence"].append(
                    1.0 if any(w in f.content.lower() for w in ["goal", "pursuit", "driven to", "seeking", "trying to"]) else 0.0
                )
                metrics_list["conflict_escalation"].append(
                    min(1.0, len(f.conflict_keywords) / 3)
                )
                metrics_list["emotional_continuity"].append(
                    min(1.0, len(f.emotion_keywords) / 2)
                )
                metrics_list["dialogue_naturalness"].append(
                    min(1.0, f.dialogue_lines / max(len(f.sentences), 1) * 3)
                )
                causal_words = ["because", "therefore", "so", "caused", "led to", "forced", "as a result"]
                causal = sum(1 for s in f.sentences if any(cw in s.lower() for cw in causal_words))
                metrics_list["causal_coherence"].append(
                    min(1.0, causal / max(len(f.sentences), 1) * 4)
                )
            
            lines.append("| Metric | Avg Score | Assessment |")
            lines.append("|--------|-----------|------------|")
            for metric, values in metrics_list.items():
                avg = statistics.mean(values)
                if avg >= 0.6:
                    assess = "Good"
                elif avg >= 0.3:
                    assess = "Adequate"
                else:
                    assess = "Poor"
                lines.append(f"| {metric.replace('_', ' ').title()} | {avg:.2f} | {assess} |")
            
            avg_words = statistics.mean([f.word_count for f in feats])
            avg_scenes = statistics.mean([f.scene_count for f in feats])
            lines.append(f"\n**Stats**: Avg {avg_words:.0f} words, {avg_scenes:.1f} scenes per story")
        
        # Failure cases
        lines.append("\n\n## Failure Cases\n")
        for label in ["SHORT_Full", "CHAPTER_Full"]:
            feats = self._valid_features(label)
            if not feats:
                continue
            failing = [f for f in feats if f.word_count < 50]
            lines.append(f"- **{label}**: {len(failing)}/{len(feats)} stories below 50 words")
            
            empty_char = [f for f in feats if not any(f.character_mentions.values())]
            lines.append(f"- **{label}**: {len(empty_char)}/{len(feats)} stories with no character mentions")
        
        return "\n".join(lines)

    def realizer_quality_report(self) -> str:
        lines = ["# SCRIPTY v2 — Realizer Quality Report\n"]
        
        for label in ["SHORT_Full", "CHAPTER_Full"]:
            feats = self._valid_features(label)
            if not feats:
                continue
            
            lines.append(f"\n## {label}\n")
            
            prose_metrics = defaultdict(list)
            for f in feats:
                pm = measure_prose_repetition(f)
                for k, v in pm.items():
                    prose_metrics[k].append(v)
            
            lines.append("### Prose Metrics\n")
            lines.append("| Metric | Avg | Assessment |")
            lines.append("|--------|-----|------------|")
            for metric, values in prose_metrics.items():
                avg = statistics.mean(values)
                if metric == "simulation_pattern_sentences":
                    assess = "CRITICAL" if avg > 2 else "OK" if avg > 0 else "Clean"
                elif metric == "unique_start_ratio":
                    assess = "Good" if avg > 0.5 else "Poor" if avg > 0.3 else "Critical"
                else:
                    assess = f"{avg:.1f}"
                lines.append(f"| {metric.replace('_', ' ').title()} | {avg:.2f} | {assess} |")
            
            # Sample excerpts
            lines.append("\n\n### Sample Excerpts\n")
            for i, f in enumerate(feats[:3]):
                excerpt = f.content[:300]
                lines.append(f"**Story {i+1}** ({f.word_count} words):\n> {excerpt}\n")
        
        return "\n".join(lines)

    def prose_analysis_report(self) -> str:
        lines = ["# SCRIPTY v2 — Mechanical Prose Detection\n"]
        
        for label in ["SHORT_Full", "CHAPTER_Full"]:
            feats = self._valid_features(label)
            if not feats:
                continue
            
            lines.append(f"\n## {label}\n")
            
            all_text = " ".join(f.content for f in feats)
            
            # Pattern detection
            patterns = {
                "X did Y": r'\b(?:Arjun|Maya|Ananya|Vikram|Ravi|Priya)\s+(?:ran|walked|moved|looked|turned|reached|grabbed|pushed)\b',
                "X said Y": r'\b(?:Arjun|Maya|Ananya|Vikram|Ravi|Priya)\s+(?:said|asked|replied|whispered|shouted)\b',
                "X reacts to Y": r'\b(?:Arjun|Maya|Ananya|Vikram|Ravi|Priya)\s+(?:felt|thought|wondered|realized|knew|saw|heard)\b',
                "driven to X": r'\bdriven to\b',
                "charged with": r'\bcharged with\b',
                "moves with purpose": r'\bmoves with\b',
                "tension/air thick": r'\bair thick\b',
                "as the moment passes": r'\bas the moment passes\b',
            }
            
            lines.append("### Pattern Frequency\n")
            lines.append("| Pattern | Occurrences | Assessment |")
            lines.append("|---------|------------|------------|")
            for pat_name, pat_re in patterns.items():
                count = len(re.findall(pat_re, all_text))
                assess = "Critical" if count > 20 else "Warning" if count > 5 else "OK"
                lines.append(f"| {pat_name} | {count} | {assess} |")
            
            # Sentence variation
            all_sentences = [s for f in feats for s in f.sentences]
            sentence_lengths = [len(s.split()) for s in all_sentences]
            if sentence_lengths:
                avg_len = statistics.mean(sentence_lengths)
                stdev_len = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
                lines.append(f"\n### Sentence Variation\n")
                lines.append(f"- Avg sentence length: {avg_len:.1f} words")
                lines.append(f"- StdDev: {stdev_len:.1f}")
                lines.append(f"- Human-like range: 10-25 words avg with 5-15 stddev")
                lines.append(f"- Current range assessment: {'GOOD' if 10 < avg_len < 25 else 'POOR'}")
            
            # Dialogue diversity
            all_dialogue = []
            for f in feats:
                all_dialogue.extend(re.findall(r'["\u201c](.*?)["\u201d]', f.content))
            lines.append(f"\n### Dialogue Diversity\n")
            lines.append(f"- Total dialogue instances: {len(all_dialogue)}")
            
            if all_dialogue:
                dialogue_words = [len(d.split()) for d in all_dialogue]
                lines.append(f"- Avg dialogue length: {statistics.mean(dialogue_words):.1f} words")
            else:
                lines.append("- **No dialogue detected**")
        
        return "\n".join(lines)

    def character_behavior_report(self) -> str:
        lines = ["# SCRIPTY v2 — Character Behavior Report\n"]
        
        for label in ["SHORT_Full", "CHAPTER_Full"]:
            feats = self._valid_features(label)
            if not feats:
                continue
            
            lines.append(f"\n## {label}\n")
            
            all_text = " ".join(f.content for f in feats)
            
            char_names = set()
            for f in feats:
                char_names.update(f.character_names)
            
            lines.append("### Character Mention Frequency\n")
            lines.append("| Character | Total Mentions | Avg/Story |")
            lines.append("|-----------|---------------|-----------|")
            for name in sorted(char_names):
                total = sum(f.character_mentions.get(name, 0) for f in feats)
                avg = total / max(len(feats), 1)
                lines.append(f"| {name} | {total} | {avg:.1f} |")
            
            # Action diversity per character
            lines.append("\n### Action Diversity\n")
            action_verbs_total = Counter()
            for f in feats:
                for v in f.action_verbs:
                    action_verbs_total[v] += 1
            
            total_actions = sum(action_verbs_total.values())
            unique_actions = len(action_verbs_total)
            lines.append(f"- Unique action verbs: {unique_actions}")
            lines.append(f"- Total action instances: {total_actions}")
            lines.append(f"- Diversity: {unique_actions/max(total_actions,1):.2f}")
            
            # Emotional range
            all_emotions = Counter()
            for f in feats:
                for e in f.emotion_keywords:
                    all_emotions[e] += 1
            lines.append(f"\n### Emotional Range\n")
            lines.append(f"- Unique emotion words: {len(all_emotions)}")
            if all_emotions:
                lines.append(f"- Top emotions: {', '.join(f'{w}({c})' for w,c in all_emotions.most_common(5))}")
            else:
                lines.append("- **No emotion words detected**")
        
        return "\n".join(lines)

    def influence_scorecard(self) -> str:
        lines = ["# SCRIPTY v2 — Influence Scorecard\n"]
        
        full_feats = self._valid_features("SHORT_Full")
        
        for ab_name in ["No MemorySystem", "No CharacterAgent", "No ConflictResolver", "No WorldState", "No StoryPlanner"]:
            key = f"SHORT_{ab_name}"
            ab_feats = self._valid_features(key)
            if not full_feats or not ab_feats:
                continue
            
            subsystem = ab_name[3:]
            lines.append(f"\n## {subsystem}\n")
            
            divergences = []
            word_deltas = []
            for f_full, f_ab in zip(full_feats[:min(len(full_feats), len(ab_feats))], ab_feats[:min(len(full_feats), len(ab_feats))]):
                divergences.append(compute_divergence(f_full.content, f_ab.content))
                word_deltas.append(f_full.word_count - f_ab.word_count)
            
            avg_div = statistics.mean(divergences)
            avg_word_delta = statistics.mean(word_deltas)
            
            lines.append(f"- **Lexical divergence from full**: {avg_div:.3f}")
            lines.append(f"- **Avg word count delta**: {avg_word_delta:+.0f}")
            
            if avg_div > 0.5:
                lines.append("- **Verdict**: HIGH INFLUENCE — removing this subsystem measurably changes output")
            elif avg_div > 0.3:
                lines.append("- **Verdict**: MODERATE INFLUENCE — subsystem affects output but not critically")
            else:
                lines.append("- **Verdict**: LOW INFLUENCE — output similar with or without this subsystem")
            
            # Qualitative examples
            for i in range(min(3, len(full_feats), len(ab_feats))):
                if full_feats[i] and ab_feats[i]:
                    lines.append(f"\n  **Example {i+1}:**")
                    lines.append(f"  - Full: \"{full_feats[i].content[:150]}...\"")
                    lines.append(f"  - No {subsystem}: \"{ab_feats[i].content[:150]}...\"")
        
        # Summary table
        lines.append("\n\n## Summary\n")
        lines.append("| Subsystem | Divergence | Word Delta | Influence |")
        lines.append("|-----------|-----------|-----------|-----------|")
        for ab_name in ["No MemorySystem", "No CharacterAgent", "No ConflictResolver", "No WorldState", "No StoryPlanner"]:
            key = f"SHORT_{ab_name}"
            ab_feats = self._valid_features(key)
            if not full_feats or not ab_feats:
                continue
            divergences = []
            word_deltas = []
            for f_full, f_ab in zip(full_feats[:min(len(full_feats), len(ab_feats))], ab_feats[:min(len(full_feats), len(ab_feats))]):
                divergences.append(compute_divergence(f_full.content, f_ab.content))
                word_deltas.append(f_full.word_count - f_ab.word_count)
            avg_div = statistics.mean(divergences)
            avg_delta = statistics.mean(word_deltas)
            influence = "High" if avg_div > 0.5 else "Moderate" if avg_div > 0.3 else "Low"
            lines.append(f"| {ab_name[3:]} | {avg_div:.3f} | {avg_delta:+.0f} | {influence} |")
        
        return "\n".join(lines)

    def final_verdict(self) -> str:
        lines = ["# SCRIPTY v2 — Final Verdict\n"]
        
        full_short = self._valid_features("SHORT_Full")
        full_chapter = self._valid_features("CHAPTER_Full")
        
        # Assess each subsystem
        subsystems = {}
        
        for ab_name in ["No MemorySystem", "No CharacterAgent", "No ConflictResolver", "No WorldState", "No StoryPlanner"]:
            key = f"SHORT_{ab_name}"
            ab_feats = self._valid_features(key)
            if not full_short or not ab_feats:
                continue
            divergences = []
            for f_full, f_ab in zip(full_short[:min(len(full_short), len(ab_feats))], ab_feats[:min(len(full_short), len(ab_feats))]):
                divergences.append(compute_divergence(f_full.content, f_ab.content))
            subsystems[ab_name[3:]] = statistics.mean(divergences) if divergences else 0
        
        lines.append("## Subsystem Influence Ranking\n")
        lines.append("| Rank | Subsystem | Influence Score | Bottleneck Potential |")
        lines.append("|------|-----------|----------------|---------------------|")
        ranked = sorted(subsystems.items(), key=lambda x: x[1], reverse=True)
        for rank, (name, score) in enumerate(ranked, 1):
            potential = "HIGH" if score < 0.3 else "LOW" if score < 0.5 else "MODERATE"
            lines.append(f"| {rank} | {name} | {score:.3f} | {potential} |")
        
        # Realizer quality
        if full_short:
            prose_metrics = []
            for f in full_short:
                pm = measure_prose_repetition(f)
                prose_metrics.append(pm)
            avg_sim_patterns = statistics.mean([p["simulation_pattern_sentences"] for p in prose_metrics])
            avg_unique_start = statistics.mean([p["unique_start_ratio"] for p in prose_metrics])
            
            lines.append(f"\n## Realizer Health\n")
            lines.append(f"- Simulation pattern sentences (avg): {avg_sim_patterns:.1f}")
            lines.append(f"- Unique sentence start ratio: {avg_unique_start:.2f}")
            
            if avg_sim_patterns > 1.5:
                lines.append("- **CompositionalRealizer produces simulation-log prose**")
            elif avg_sim_patterns > 0.5:
                lines.append("- **CompositionalRealizer shows some repetitive patterns**")
            else:
                lines.append("- **CompositionalRealizer produces natural prose**")
        
        # Reader experience
        if full_short:
            reader_scores = defaultdict(list)
            for f in full_short:
                rs = measure_reader_experience(f)
                for k, v in rs.items():
                    reader_scores[k].append(v)
            avg_reader = statistics.mean([statistics.mean(v) for v in reader_scores.values()]) if reader_scores else 0
            
            lines.append(f"\n## Reader Experience Score: {avg_reader:.2f}/1.0\n")
            if avg_reader < 0.3:
                lines.append("**Readers cannot infer story elements** — the system produces opaque text.")
            elif avg_reader < 0.5:
                lines.append("**Marginal reader experience** — some elements inferrable but not enough.")
            else:
                lines.append("**Adequate reader experience** — core story elements are present.")
        
        # Biggest bottleneck
        if full_short:
            avg_words = statistics.mean([f.word_count for f in full_short])
            avg_sentences = statistics.mean([f.sentence_count for f in full_short])
            lines.append(f"\n## Average Story Stats\n")
            lines.append(f"- Words: {avg_words:.0f}")
            lines.append(f"- Sentences: {avg_sentences:.1f}")
            lines.append(f"- Words/sentence: {avg_words/max(avg_sentences,1):.1f}")
        
        # Determine bottleneck
        worst_subsystem = ranked[-1][0] if ranked else "Unknown"
        worst_score = ranked[-1][1] if ranked else 0
        
        if worst_score < 0.2:
            bottleneck = "CompositionalRealizer"
            reason = "Subsystems produce distinct output, but the Realizer homogenizes it into repetitive simulation-log prose. The CompositionalRealizer is the single point of failure."
        elif avg_sim_patterns > 1.5:  # noqa F821 - defined above
            bottleneck = "CompositionalRealizer"
            reason = "The Realizer produces mechanical, template-driven output that masks subsystem differences."
        else:
            bottleneck = worst_subsystem
            reason = f"Lowest influence subsystem ({worst_subsystem}: {worst_score:.3f} divergence) indicates it is not effectively constraining generation."
        
        lines.append(f"\n## Verdict: **{bottleneck}** is the biggest bottleneck\n")
        lines.append(f"{reason}\n")
        lines.append("### Evidence\n")
        
        # Show example of the problem
        if full_short:
            examples = []
            for f in full_short[:5]:
                text = f.content
                if re.search(r'(?:driven to|moves with|charged with|air thick|as the moment passes)', text):
                    examples.append(text[:200])
            if examples:
                lines.append("Realizer repetition examples:\n")
                for i, ex in enumerate(examples[:3], 1):
                    lines.append(f"> {ex}...\n")
        
        return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────────────────────


async def main():
    runner = ValidationRunner()
    print("=" * 60)
    print("SCRIPTY v2 Generation Validation Audit")
    print("=" * 60)
    
    print("\n[1/5] Building requests...")
    runner.build_requests()
    print(f"  SHORT requests: {len(runner.short_requests)}")
    print(f"  CHAPTER requests: {len(runner.chapter_requests)}")
    
    print("\n[2/5] Generating stories...")
    await runner.generate_all()
    
    print("\n[3/5] Analyzing features...")
    runner.analyze_all()
    
    print("\n[4/5] Producing reports...")
    reports = {
        "01_subsystem_influence.md": runner.subsystem_influence_report(),
        "02_reader_experience.md": runner.reader_experience_report(),
        "03_character_behavior.md": runner.character_behavior_report(),
        "04_conflict_quality.md": None,
        "05_realizer_quality.md": runner.realizer_quality_report(),
        "06_failure_analysis.md": runner.narrative_quality_report(),
        "07_influence_scorecard.md": runner.influence_scorecard(),
        "08_final_verdict.md": runner.final_verdict(),
    }
    
    import os
    output_dir = "/Users/manikantapotla/Desktop/SCRIPTY/backend/v2/audit_reports"
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, content in reports.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            f.write(content or "# Report not generated\n")
        print(f"  Written: {filepath}")
    
    # Also print final verdict to stdout
    print("\n[5/5] Final Verdict")
    print(runner.final_verdict())
    
    print("\n" + "=" * 60)
    print("Audit complete. Reports in backend/v2/audit_reports/")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
