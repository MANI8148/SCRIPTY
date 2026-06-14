from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Iterator


@dataclass
class ParsedDocument:
    source_path: str
    title: str
    author: str = ""
    chapters: List["ParsedChapter"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedChapter:
    number: int
    title: str = ""
    scenes: List["ParsedScene"] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)


@dataclass
class ParsedScene:
    number: int
    paragraphs: List[str] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        pass

    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        pass

    def extract_title_from_path(self, file_path: str) -> str:
        import os
        basename = os.path.basename(file_path)
        name, _ = os.path.splitext(basename)
        clean = name.replace("_", " ").replace("-", " ").replace(".", " ")
        clean = " ".join(w.capitalize() for w in clean.split() if w)
        return clean

    def detect_chapter_boundaries(self, text: str) -> List[int]:
        import re
        boundaries = [0]
        patterns = [
            r'^Chapter\s+\d+',
            r'^CHAPTER\s+\d+',
            r'^\d+\.\s+',
            r'^Part\s+\d+',
            r'^Book\s+\w+',
            r'^\d{4}',
        ]
        lines = text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            for pat in patterns:
                if re.match(pat, stripped):
                    boundaries.append(i)
                    break
        return sorted(set(boundaries))

    def detect_scene_boundaries(self, paragraphs: List[str]) -> List[int]:
        boundaries = [0]
        scene_markers = ["---", "***", "✦", "✧", "◆", "▪", "* * *"]
        for i, para in enumerate(paragraphs):
            stripped = para.strip()
            if any(marker in stripped for marker in scene_markers):
                if len(stripped) < 10:
                    boundaries.append(i)
            if stripped and len(stripped.split()) <= 2 and stripped.isupper():
                boundaries.append(i)
        boundaries.append(len(paragraphs))
        return sorted(set(boundaries))
