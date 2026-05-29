from __future__ import annotations

import json
import statistics
import uuid
import datetime
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ExperimentRecord:
    run_id: str             # UUID4
    random_seed: int
    generation_parameters: dict
    subsystem_config: dict  # enabled/disabled flags
    metrics: dict           # all EvaluationPipeline metric values
    generation_timestamp: str  # ISO 8601


class ExperimentTracker:
    def __init__(
        self,
        log_path: str = "backend/research_output/experiments.jsonl",
    ) -> None:
        self.log_path = Path(log_path)

    def record(
        self,
        run: ExperimentRecord | None = None,
        *,
        random_seed: int | None = None,
        generation_parameters: dict | None = None,
        subsystem_config: dict | None = None,
        metrics: dict | None = None,
    ) -> ExperimentRecord:
        """Append a single JSON line to the log file.

        Creates the file and parent directories if they don't exist.
        """
        if run is None:
            run = make_experiment_record(
                random_seed=random_seed if random_seed is not None else 0,
                generation_parameters=generation_parameters or {},
                subsystem_config=subsystem_config or {},
                metrics=metrics or {},
            )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(run), sort_keys=True) + "\n")
        return run

    def load_all(self) -> list[ExperimentRecord]:
        """Read all lines from the log file and return list of ExperimentRecord objects."""
        if not self.log_path.exists():
            return []
        records = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(ExperimentRecord(**json.loads(line)))
        return records

    def filter_runs(self, **config_filters) -> list[ExperimentRecord]:
        """Load all records and filter by matching subsystem_config keys.

        kwargs are matched against subsystem_config dict values.
        """
        records = self.load_all()
        result = []
        for record in records:
            match = all(
                record.subsystem_config.get(key) == value
                for key, value in config_filters.items()
            )
            if match:
                result.append(record)
        return result

    def aggregate(self, metric_key: str, **config_filters) -> dict:
        """Return mean, std, min, max for the given metric_key across filtered runs.

        Uses the statistics module for mean/stdev.
        """
        runs = self.filter_runs(**config_filters) if config_filters else self.load_all()
        values = [
            float(run.metrics[metric_key])
            for run in runs
            if metric_key in run.metrics
        ]
        if not values:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        return {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
        }


def make_experiment_record(
    random_seed: int,
    generation_parameters: dict,
    subsystem_config: dict,
    metrics: dict,
) -> ExperimentRecord:
    """Convenience factory that generates run_id and timestamp automatically."""
    return ExperimentRecord(
        run_id=str(uuid.uuid4()),
        random_seed=random_seed,
        generation_parameters=generation_parameters,
        subsystem_config=subsystem_config,
        metrics=metrics,
        generation_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
