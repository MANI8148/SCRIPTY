from __future__ import annotations

from backend.research.scene_dataset_generator import SCENE_TYPES


class SceneModelComparator:
    def compare(self, predictors: dict[str, object], examples: list) -> dict[str, dict]:
        return {name: self.evaluate(predictor, examples) for name, predictor in predictors.items()}

    def evaluate(self, predictor: object, examples: list) -> dict:
        if not examples:
            return {"accuracy": 0.0, "top3_accuracy": 0.0, "confusion_matrix": {}}
        correct = 0
        top3 = 0
        matrix = {actual: {predicted: 0 for predicted in SCENE_TYPES} for actual in SCENE_TYPES}
        per_genre: dict[str, list[int]] = {}
        for example in examples:
            distribution = predictor.rank_scene_candidates(example.features)
            ranked = sorted(distribution, key=distribution.__getitem__, reverse=True)
            predicted = ranked[0]
            actual = example.target
            correct += int(predicted == actual)
            top3 += int(actual in ranked[:3])
            matrix.setdefault(actual, {scene_type: 0 for scene_type in SCENE_TYPES})
            matrix[actual][predicted] = matrix[actual].get(predicted, 0) + 1
            genre = str(example.features.get("genre", "general"))
            per_genre.setdefault(genre, [0, 0])
            per_genre[genre][0] += int(predicted == actual)
            per_genre[genre][1] += 1
        return {
            "accuracy": round(correct / len(examples), 6),
            "top3_accuracy": round(top3 / len(examples), 6),
            "confusion_matrix": matrix,
            "per_genre_accuracy": {
                genre: round(values[0] / max(1, values[1]), 6)
                for genre, values in per_genre.items()
            },
            "failure_modes": [
                f"{actual}->{predicted}: {count}"
                for actual, row in matrix.items()
                for predicted, count in row.items()
                if actual != predicted and count
            ],
        }
