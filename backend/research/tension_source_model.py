from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ConflictSource:
    source_type: str  # "internal", "interpersonal", "environmental"
    intensity: float  # [0.0, 1.0]
    description: str

class TensionSourceModel:
    """
    Models narrative tension dynamically by aggregating active conflict sources.
    This replaces static rule-based tension curves with an emergent
    tension state driven by narrative events.
    """
    def __init__(self, decay_rate: float = 0.05):
        self.active_sources: list[ConflictSource] = []
        self.decay_rate = decay_rate
        
    def add_conflict(self, source_type: str, intensity: float, description: str) -> None:
        self.active_sources.append(ConflictSource(source_type, intensity, description))
        logger.debug(
            "conflict_source_added",
            extra={"source_type": source_type, "intensity": intensity, "description": description}
        )
        
    def resolve_conflict(self, source_type: str) -> None:
        """Remove all conflicts of a specific type."""
        self.active_sources = [s for s in self.active_sources if s.source_type != source_type]
        
    def step_time(self) -> None:
        """Decay conflict intensities over time to simulate acclimatization."""
        for source in self.active_sources:
            source.intensity = max(0.0, source.intensity - self.decay_rate)
        # Remove depleted sources
        self.active_sources = [s for s in self.active_sources if s.intensity > 0.05]
        
    def compute_current_tension(self) -> float:
        """Calculate the overall tension using a sub-additive formula."""
        if not self.active_sources:
            return 0.2  # Baseline narrative tension
            
        # Sub-additive aggregation: T_total = 1 - product(1 - T_i)
        combined = 1.0
        for source in self.active_sources:
            combined *= (1.0 - source.intensity)
            
        final_tension = min(max(1.0 - combined, 0.0), 1.0)
        return final_tension
