"""Load Gutenberg corpus files for n-gram training."""

from __future__ import annotations

import glob
import os
from pathlib import Path


class CorpusLoader:
    """Loads and iterates over Gutenberg text files.

    Handles encoding detection, line-level reading, and file discovery.
    """

    def __init__(self, corpus_dir: str | Path) -> None:
        self.corpus_dir = Path(corpus_dir)
        self._file_paths: list[Path] = []
        self._scan_files()

    def _scan_files(self) -> None:
        pattern = str(self.corpus_dir / "*.txt")
        self._file_paths = sorted(Path(p) for p in glob.glob(pattern))

    @property
    def file_count(self) -> int:
        return len(self._file_paths)

    @property
    def file_paths(self) -> list[Path]:
        return list(self._file_paths)

    def iter_lines(self, max_files: int | None = None) -> list[str]:
        """Read all lines from all files, returning a flat list."""
        all_lines: list[str] = []
        paths = self._file_paths[:max_files] if max_files else self._file_paths
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                all_lines.extend(text.splitlines())
            except Exception:
                continue
        return all_lines

    def iter_sentences(
        self, max_files: int | None = None
    ) -> list[list[str]]:
        """Read all lines, split into sentences, return list of token lists."""
        from nltk.tokenize import sent_tokenize

        all_sentences: list[list[str]] = []
        paths = self._file_paths[:max_files] if max_files else self._file_paths
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                for sent in sent_tokenize(text):
                    tokens = _tokenize(sent)
                    if len(tokens) >= 3:
                        all_sentences.append(tokens)
            except Exception:
                continue
        return all_sentences


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercased tokens."""
    from nltk.tokenize import word_tokenize
    tokens = word_tokenize(text.lower())
    return [t for t in tokens if any(c.isalpha() for c in t)]
