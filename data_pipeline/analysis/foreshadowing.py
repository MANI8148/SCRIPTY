from typing import List, Dict, Tuple
import re
import logging
from collections import defaultdict
import numpy as np

from data_pipeline.schema.fragment import NarrativeFragment, ForeshadowingLink
from data_pipeline.config import DEDUP_CONFIG


logger = logging.getLogger(__name__)


FORESHADOWING_PATTERNS = {
    "direct": [
        "little did", "would later", "would soon", "would come to",
        "didn't know it yet", "did not know it yet",
        "had no way of knowing", "could not have known",
    ],
    "ominous": [
        "omen", "portent", "foreboding", "premonition",
        "sign", "warning", "threat", "dread",
    ],
    "setup": [
        "if only", "had he known", "what he didn't know",
        "unaware", "unknowingly", "unsuspecting",
        "the last time", "never again",
    ],
}

PAYOFF_PATTERNS = [
    "as it turned out", "now he understood", "now she understood",
    "finally realized", "in the end", "it became clear",
    "the truth was", "what he didn't know", "what she didn't know",
]


class ForeshadowingExtractor:
    def __init__(self):
        self._dedup_model = None

    def _load_model(self):
        if self._dedup_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._dedup_model = SentenceTransformer(DEDUP_CONFIG["model_name"])
            except ImportError:
                self._dedup_model = None

    def execute(self, fragments: List[NarrativeFragment]) -> List[ForeshadowingLink]:
        self._load_model()

        setups = []
        payoffs = []

        for frag in fragments:
            fl = self._classify_foreshadowing(frag.text)
            if fl == "setup":
                setups.append(frag)
            elif fl == "payoff":
                payoffs.append(frag)

        links = self._link_setups_to_payoffs(setups, payoffs)
        logger.info(f"Found {len(links)} foreshadowing links ({len(setups)} setups, {len(payoffs)} payoffs)")
        return links

    def _classify_foreshadowing(self, text: str) -> str:
        text_lower = text.lower()
        for fw_type, patterns in FORESHADOWING_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return "setup"
        for pattern in PAYOFF_PATTERNS:
            if pattern in text_lower:
                return "payoff"
        return ""

    def _link_setups_to_payoffs(self, setups: List[NarrativeFragment], payoffs: List[NarrativeFragment]) -> List[ForeshadowingLink]:
        links = []
        if not setups or not payoffs:
            return links

        if self._dedup_model is not None:
            setup_texts = [s.text[:256] for s in setups]
            payoff_texts = [p.text[:256] for p in payoffs]
            setup_embs = self._dedup_model.encode(setup_texts, show_progress_bar=False)
            payoff_embs = self._dedup_model.encode(payoff_texts, show_progress_bar=False)

            for si, setup in enumerate(setups):
                for pi, payoff in enumerate(payoffs):
                    if payoff.chapter <= setup.chapter:
                        continue

                    sim = np.dot(setup_embs[si], payoff_embs[pi]) / (
                        np.linalg.norm(setup_embs[si]) * np.linalg.norm(payoff_embs[pi])
                    )
                    sim = float(np.clip(sim, 0, 1))

                    if sim >= 0.35:
                        link = ForeshadowingLink(
                            source_book=setup.source_book,
                            author=setup.author,
                            setup_fragment_id=setup.id,
                            setup_text=setup.text[:200],
                            setup_chapter=setup.chapter,
                            payoff_fragment_id=payoff.id,
                            payoff_text=payoff.text[:200],
                            payoff_chapter=payoff.chapter,
                            distance=payoff.chapter - setup.chapter,
                            foreshadowing_type=self._classify_foreshadowing(setup.text),
                            confidence=sim,
                        )
                        links.append(link)
        else:
            for setup in setups:
                for payoff in payoffs:
                    if payoff.chapter > setup.chapter:
                        link = ForeshadowingLink(
                            source_book=setup.source_book,
                            author=setup.author,
                            setup_fragment_id=setup.id,
                            setup_text=setup.text[:200],
                            setup_chapter=setup.chapter,
                            payoff_fragment_id=payoff.id,
                            payoff_text=payoff.text[:200],
                            payoff_chapter=payoff.chapter,
                            distance=payoff.chapter - setup.chapter,
                            foreshadowing_type=self._classify_foreshadowing(setup.text),
                            confidence=0.5,
                        )
                        links.append(link)

        links.sort(key=lambda x: -x.confidence)
        return links[:max(1, len(links) // 2)]
