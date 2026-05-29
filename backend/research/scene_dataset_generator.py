from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCENE_TYPES = ["action", "dialogue", "introspection", "description", "transition"]


@dataclass(frozen=True)
class SceneTrainingExample:
    features: dict[str, float | str]
    target: str


class SceneFeatureExtractor:
    """Extracts compact ML features from scene context and previous scene state."""

    GENRE_IDS = {
        "general": 0.0,
        "adventure": 1.0,
        "fantasy": 2.0,
        "gothic": 3.0,
        "historical": 4.0,
        "historical fiction": 4.0,
        "mystery": 5.0,
        "social fiction": 6.0,
        "speculative": 7.0,
    }
    SCENE_IDS = {scene_type: float(index) for index, scene_type in enumerate(SCENE_TYPES)}
    STAGE_IDS = {"unaware": 0.0, "discovering": 1.0, "confronting": 2.0, "resolving": 3.0}

    def extract(self, context: dict, *, scene_index: int = 0, scene_count: int = 1) -> dict[str, float | str]:
        genre = str(context.get("genre", "general")).lower()
        protagonist_state = context.get("protagonist_state") or context.get("protagonist_arc_stage", "unaware")
        antagonist_state = context.get("antagonist_state") or context.get("antagonist_arc_stage", "unaware")
        previous_scene_type = str(context.get("previous_scene_type", "description")).lower()
        unresolved = context.get("unresolved_conflicts", 0)
        if isinstance(unresolved, list):
            unresolved = len(unresolved)
        scene_count = max(1, int(scene_count))
        return {
            "genre": genre,
            "genre_id": self.GENRE_IDS.get(genre, 0.0),
            "scene_position": round(scene_index / max(1, scene_count - 1), 6),
            "tension": round(float(context.get("tension", context.get("target_tension", 0.0))), 6),
            "protagonist_stage": str(protagonist_state),
            "protagonist_stage_id": self.STAGE_IDS.get(str(protagonist_state), 0.0),
            "antagonist_stage": str(antagonist_state),
            "antagonist_stage_id": self.STAGE_IDS.get(str(antagonist_state), 0.0),
            "unresolved_conflicts": float(unresolved),
            "previous_scene_type": previous_scene_type,
            "previous_scene_type_id": self.SCENE_IDS.get(previous_scene_type, 0.0),
        }

    def vectorize(self, features: dict[str, float | str]) -> list[float]:
        return [
            float(features.get("genre_id", 0.0)),
            float(features.get("scene_position", 0.0)),
            float(features.get("tension", 0.0)),
            float(features.get("protagonist_stage_id", 0.0)),
            float(features.get("antagonist_stage_id", 0.0)),
            float(features.get("unresolved_conflicts", 0.0)),
            float(features.get("previous_scene_type_id", 0.0)),
        ]


class SceneDatasetGenerator:
    def __init__(self, feature_extractor: SceneFeatureExtractor | None = None) -> None:
        self.feature_extractor = feature_extractor or SceneFeatureExtractor()

    def examples_from_chapters(self, chapters: list[Any], base_context: dict | None = None) -> list[SceneTrainingExample]:
        base_context = base_context or {}
        examples: list[SceneTrainingExample] = []
        previous_scene_type = str(base_context.get("previous_scene_type", "description"))
        for chapter in chapters:
            scenes = list(getattr(chapter, "scenes", []) or [])
            for index, scene in enumerate(scenes[:-1]):
                next_scene = scenes[index + 1]
                scene_type = getattr(getattr(scene, "scene_type", ""), "value", getattr(scene, "scene_type", previous_scene_type))
                target = getattr(getattr(next_scene, "scene_type", ""), "value", getattr(next_scene, "scene_type", "description"))
                context = {
                    **base_context,
                    "previous_scene_type": str(scene_type),
                    "tension": float(getattr(scene, "tension_score", 0.0)),
                }
                features = self.feature_extractor.extract(context, scene_index=index, scene_count=len(scenes))
                examples.append(SceneTrainingExample(features=features, target=str(target)))
                previous_scene_type = str(scene_type)
        return examples

    def generate_synthetic_dataset(self, book_count: int = 100, genres: list[str] | None = None) -> list[SceneTrainingExample]:
        genres = genres or ["historical", "mystery", "adventure", "social fiction"]
        examples: list[SceneTrainingExample] = []
        for book_index in range(book_count):
            genre = genres[book_index % len(genres)]
            previous = "description"
            scene_count = 8 + (book_index % 6)
            for scene_index in range(scene_count):
                position = scene_index / max(1, scene_count - 1)
                tension = min(1.0, 0.15 + position * 0.75)
                if position > 0.85:
                    target = "transition"
                elif tension > 0.65:
                    target = "action"
                elif tension > 0.45:
                    target = "dialogue"
                elif scene_index % 3 == 0:
                    target = "introspection"
                else:
                    target = "description"
                context = {
                    "genre": genre,
                    "previous_scene_type": previous,
                    "tension": tension,
                    "protagonist_arc_stage": self._stage_for_position(position),
                    "antagonist_arc_stage": self._stage_for_position(position),
                    "unresolved_conflicts": max(0, 4 - int(position * 4)),
                }
                features = self.feature_extractor.extract(context, scene_index=scene_index, scene_count=scene_count)
                examples.append(SceneTrainingExample(features=features, target=target))
                previous = target
        return examples

    def split_dataset(
        self,
        examples: list[SceneTrainingExample],
        ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
        seed: int = 7,
    ) -> dict[str, list[SceneTrainingExample]]:
        items = list(examples)
        random.Random(seed).shuffle(items)
        train_end = int(len(items) * ratios[0])
        val_end = train_end + int(len(items) * ratios[1])
        return {"train": items[:train_end], "validation": items[train_end:val_end], "test": items[val_end:]}

    def save_json(self, splits: dict[str, list[SceneTrainingExample]], path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {name: [asdict(example) for example in examples] for name, examples in splits.items()}
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target

    def save_csv(self, examples: list[SceneTrainingExample], path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "genre",
            "genre_id",
            "scene_position",
            "tension",
            "protagonist_stage",
            "protagonist_stage_id",
            "antagonist_stage",
            "antagonist_stage_id",
            "unresolved_conflicts",
            "previous_scene_type",
            "previous_scene_type_id",
            "target",
        ]
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for example in examples:
                writer.writerow({**example.features, "target": example.target})
        return target

    def _stage_for_position(self, position: float) -> str:
        if position <= 0.25:
            return "unaware"
        if position <= 0.50:
            return "discovering"
        if position <= 0.75:
            return "confronting"
        return "resolving"
