from __future__ import annotations

import argparse
import json
import math
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.research.dataset_manifest import ManifestEntry, PassageRecord, load_manifest


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z][a-zA-Z']+", text.lower()))


@dataclass(frozen=True)
class NeuralTrainingReport:
    model_path: str
    training_examples: int
    epochs: int
    final_loss: float
    validation_accuracy: float


class NeuralReranker:
    """Small one-hidden-layer neural reranker implemented with pure Python."""

    def __init__(
        self,
        input_dim: int = 6,
        hidden_dim: int = 8,
        learning_rate: float = 0.05,
        random_seed: int = 13,
    ) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.learning_rate = learning_rate
        self.random_seed = random_seed
        rng = random.Random(random_seed)
        self.w1 = [[rng.uniform(-0.2, 0.2) for _ in range(input_dim)] for _ in range(hidden_dim)]
        self.b1 = [0.0 for _ in range(hidden_dim)]
        self.w2 = [rng.uniform(-0.2, 0.2) for _ in range(hidden_dim)]
        self.b2 = 0.0

    def features(self, query: str, result: Any) -> list[float]:
        query_tokens = _tokens(query)
        doc_tokens = _tokens(result.text)
        overlap = len(query_tokens & doc_tokens) / max(1, len(query_tokens | doc_tokens))
        query_lower = query.lower()
        metadata = result.metadata or {}
        genre_hit = 1.0 if metadata.get("genre", "").replace("_", " ") in query_lower else 0.0
        region_hit = 1.0 if metadata.get("region", "").replace("_", " ") in query_lower else 0.0
        period_hit = 1.0 if metadata.get("period", "").replace("_", " ") in query_lower else 0.0
        length_norm = min(1.0, len(doc_tokens) / 500.0)
        return [min(1.0, result.score), overlap, genre_hit, region_hit, period_hit, length_norm]

    def predict_features(self, features: list[float]) -> float:
        hidden = [math.tanh(sum(weight * value for weight, value in zip(row, features)) + bias) for row, bias in zip(self.w1, self.b1)]
        logit = sum(weight * value for weight, value in zip(self.w2, hidden)) + self.b2
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit))))

    def score(self, query: str, result: Any) -> float:
        return self.predict_features(self.features(query, result))

    def rerank(self, query: str, results: list[Any]) -> list[Any]:
        return sorted(results, key=lambda result: self.score(query, result), reverse=True)

    def train(self, examples: list[tuple[list[float], int]], epochs: int = 25) -> float:
        rng = random.Random(self.random_seed)
        loss = 0.0
        for _ in range(epochs):
            rng.shuffle(examples)
            total = 0.0
            for features, label in examples:
                hidden_raw = [sum(weight * value for weight, value in zip(row, features)) + bias for row, bias in zip(self.w1, self.b1)]
                hidden = [math.tanh(value) for value in hidden_raw]
                pred = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, sum(weight * value for weight, value in zip(self.w2, hidden)) + self.b2))))
                error = pred - label
                total += -(label * math.log(max(pred, 1e-9)) + (1 - label) * math.log(max(1 - pred, 1e-9)))
                grad_logit = error
                old_w2 = self.w2[:]
                for i in range(self.hidden_dim):
                    self.w2[i] -= self.learning_rate * grad_logit * hidden[i]
                self.b2 -= self.learning_rate * grad_logit
                for i in range(self.hidden_dim):
                    grad_hidden_raw = grad_logit * old_w2[i] * (1 - hidden[i] * hidden[i])
                    for j in range(self.input_dim):
                        self.w1[i][j] -= self.learning_rate * grad_hidden_raw * features[j]
                    self.b1[i] -= self.learning_rate * grad_hidden_raw
            loss = total / max(1, len(examples))
        return loss

    def save(self, path: str | Path, report: NeuralTrainingReport | None = None) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "learning_rate": self.learning_rate,
            "random_seed": self.random_seed,
            "w1": self.w1,
            "b1": self.b1,
            "w2": self.w2,
            "b2": self.b2,
            "report": asdict(report) if report else None,
        }, indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "NeuralReranker":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls(data["input_dim"], data["hidden_dim"], data["learning_rate"], data["random_seed"])
        model.w1 = data["w1"]
        model.b1 = data["b1"]
        model.w2 = data["w2"]
        model.b2 = data["b2"]
        return model


def build_training_examples(entries: list[ManifestEntry], max_examples: int = 2000, random_seed: int = 13) -> list[tuple[list[float], int]]:
    rng = random.Random(random_seed)
    docs: list[tuple[ManifestEntry, PassageRecord]] = [(entry, passage) for entry in entries for passage in entry.passages]
    examples: list[tuple[list[float], int]] = []
    model = NeuralReranker(random_seed=random_seed)
    @dataclass(frozen=True)
    class TrainingResult:
        source_id: str
        passage_id: str
        text: str
        score: float
        metadata: dict

    for entry, passage in docs[:max_examples]:
        query = f"{entry.genre} {entry.region} {entry.period} {entry.title}"
        positive = TrainingResult(entry.source_id, passage.passage_id, passage.text, 0.75, passage.metadata)
        examples.append((model.features(query, positive), 1))
        negative_entry, negative_passage = rng.choice(docs)
        while negative_entry.source_id == entry.source_id and len(docs) > 1:
            negative_entry, negative_passage = rng.choice(docs)
        negative = TrainingResult(negative_entry.source_id, negative_passage.passage_id, negative_passage.text, 0.1, negative_passage.metadata)
        examples.append((model.features(query, negative), 0))
        if len(examples) >= max_examples:
            break
    return examples


def train_from_manifest(
    manifest_path: str = "backend/data/dataset_manifest.jsonl",
    model_path: str = "backend/research_output/models/neural_reranker.json",
    epochs: int = 25,
    max_examples: int = 2000,
    random_seed: int = 13,
) -> NeuralTrainingReport:
    entries = load_manifest(manifest_path)
    examples = build_training_examples(entries, max_examples=max_examples, random_seed=random_seed)
    split = max(1, int(len(examples) * 0.8))
    train_examples = examples[:split]
    validation_examples = examples[split:] or examples[:]
    model = NeuralReranker(random_seed=random_seed)
    final_loss = model.train(train_examples, epochs=epochs)
    correct = sum((model.predict_features(features) >= 0.5) == bool(label) for features, label in validation_examples)
    accuracy = correct / max(1, len(validation_examples))
    report = NeuralTrainingReport(model_path, len(examples), epochs, round(final_loss, 6), round(accuracy, 6))
    model.save(model_path, report)
    Path(model_path).with_suffix(".report.json").write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train SCRIPTY's lightweight neural reranker on a local manifest.")
    parser.add_argument("--manifest", default="backend/data/dataset_manifest.jsonl")
    parser.add_argument("--model", default="backend/research_output/models/neural_reranker.json")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--max-examples", type=int, default=2000)
    args = parser.parse_args()
    report = train_from_manifest(args.manifest, args.model, args.epochs, args.max_examples)
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
