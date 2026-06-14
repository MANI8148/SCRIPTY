from typing import List
import re
import logging
from collections import defaultdict

from data_pipeline.parsers.base_parser import ParsedDocument
from data_pipeline.schema.fragment import NarrativeFragment


logger = logging.getLogger(__name__)


class CharacterExtractionPass:
    def __init__(self):
        self.name_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b')

    def execute(self, documents: List[ParsedDocument], fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        book_characters = {}
        for doc in documents:
            chars = self._extract_characters_from_document(doc)
            book_characters[doc.title] = chars
            logger.info(f"Extracted {len(chars)} characters from {doc.title}")

        for frag in fragments:
            if frag.source_book in book_characters:
                present = self._find_present_characters(frag.text, book_characters[frag.source_book])
                if present:
                    existing = set(frag.participants)
                    for c in present:
                        if c not in existing:
                            frag.participants.append(c)
                    new_tags = [f"char:{c}" for c in present]
                    frag.retrieval_tags.extend(new_tags)

        return fragments

    def _extract_characters_from_document(self, doc: ParsedDocument) -> List[str]:
        candidates = defaultdict(int)
        for chapter in doc.chapters:
            for para in chapter.paragraphs[:50]:
                names = self.name_pattern.findall(para)
                for name in names:
                    if self._is_character_name(name):
                        candidates[name] += 1

        sorted_chars = sorted(candidates.items(), key=lambda x: -x[1])
        threshold = max(3, sorted_chars[0][1] * 0.1) if sorted_chars else 3
        return [name for name, count in sorted_chars if count >= threshold][:50]

    def _is_character_name(self, name: str) -> bool:
        skip_words = {
            "The", "This", "That", "These", "Those", "What", "Which", "Who", "Whom",
            "When", "Where", "Why", "How", "All", "Each", "Every", "Both", "Few",
            "Many", "Some", "Any", "No", "Not", "Only", "Just", "Then", "Than",
            "There", "Here", "Into", "Upon", "After", "Before", "Between", "Through",
            "During", "Without", "Within", "Along", "About", "Across", "Among",
            "Chapter", "Part", "Book", "Volume", "Section", "Act", "Scene",
        }
        name_lower = name.lower()
        parts = name.split()
        if len(parts) > 2:
            return False
        for part in parts:
            if part in skip_words or part.lower() in {
                "said", "was", "were", "had", "been", "would", "could", "should",
                "did", "does", "has", "have", "having", "being", "doing",
                "going", "getting", "making", "taking", "looking", "finding",
                "seeing", "coming", "going", "knowing", "thinking",
                "very", "really", "quite", "almost", "nearly", "just",
                "also", "even", "still", "already", "always", "never",
                "often", "sometimes", "usually", "finally", "eventually",
                "however", "therefore", "meanwhile", "nevertheless",
            }:
                return False
        return True

    def _find_present_characters(self, text: str, characters: List[str]) -> List[str]:
        present = []
        for char in characters:
            if char.lower() in text.lower():
                present.append(char)
        return present
