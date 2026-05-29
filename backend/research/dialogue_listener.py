from __future__ import annotations

import logging
from backend.research.memory_manager import CharacterRecord

logger = logging.getLogger(__name__)

class DialogueListenerModel:
    """
    Polishes and evaluates generated dialogue against character traits.
    Acts as a Polish Layer for narrative generation.
    """
    def __init__(self):
        # Static mapping of traits to expected vocabulary for heuristic evaluation
        self._trait_lexicon = {
            "curious": ["why", "how", "interesting", "tell", "explain", "?", "wonder", "discover", "secret"],
            "persistent": ["must", "will", "never", "always", "continue", "again", "won't stop", "try", "fail"],
            "secretive": ["...", "nothing", "quiet", "hide", "won't say", "forget it", "no", "private", "leave"],
            "ambitious": ["power", "control", "win", "great", "future", "success", "mine", "top", "achieve"]
        }

    def evaluate(self, character_name: str, dialogue_text: str, record: CharacterRecord | None) -> float:
        """
        Evaluate how well the dialogue text aligns with the character's registered traits.
        Returns a score from 0.0 (poor alignment) to 1.0 (excellent alignment).
        """
        if not record or not record.traits:
            return 0.5  # Neutral score if no traits known
            
        dialogue_lower = dialogue_text.lower()
        
        # Base score starts at 0.4
        score = 0.4
        matches = 0
        
        for trait in record.traits:
            trait_lower = trait.lower()
            if trait_lower in self._trait_lexicon:
                keywords = self._trait_lexicon[trait_lower]
                if any(kw in dialogue_lower for kw in keywords):
                    matches += 1
                    score += 0.3
            elif trait_lower in dialogue_lower:
                # If trait itself is mentioned or implied
                matches += 1
                score += 0.2
        
        # Penalize slightly if dialogue is extremely short and has no matches
        if matches == 0 and len(dialogue_lower.split()) > 10:
            score -= 0.1
            
        final_score = min(max(score, 0.0), 1.0)
        
        logger.debug(
            "Dialogue evaluation complete",
            extra={
                "character_name": character_name,
                "traits": record.traits,
                "score": final_score
            }
        )
        return final_score
