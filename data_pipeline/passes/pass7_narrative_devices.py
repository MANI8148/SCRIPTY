from typing import List
import re
import logging
from collections import defaultdict

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category
from data_pipeline.config import EXTRACTION_CONFIG


logger = logging.getLogger(__name__)


class NarrativeDeviceExtractionPass:
    def execute(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        for frag in fragments:
            devices = self._detect_devices(frag.text)
            for device in devices:
                frag.category = Category.NARRATIVE_DEVICES.value
                frag.subcategory = device
                frag.metadata["narrative_device"] = device
                frag.retrieval_tags.append(f"device:{device}")

        return fragments

    def _detect_devices(self, text: str) -> List[str]:
        text_lower = text.lower()
        detected = []

        for device, indicators in EXTRACTION_CONFIG["narrative_device_indicators"].items():
            for ind in indicators:
                if ind in text_lower:
                    detected.append(device)
                    break

        return detected
