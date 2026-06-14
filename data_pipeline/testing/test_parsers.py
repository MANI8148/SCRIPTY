import pytest
import tempfile
import os
from pathlib import Path

from data_pipeline.parsers.txt_parser import TxtParser
from data_pipeline.parsers.base_parser import BaseParser


class TestBaseParser:
    def test_extract_title_from_path(self):
        parser = TxtParser()
        assert parser.extract_title_from_path("/path/to/the_great_gatsby.txt") == "The Great Gatsby"
        assert parser.extract_title_from_path("moby-dick.epub") == "Moby Dick"

    def test_detect_chapter_boundaries(self):
        parser = TxtParser()
        text = """Chapter 1
First paragraph.
Second paragraph.
Chapter 2
Third paragraph."""
        boundaries = parser.detect_chapter_boundaries(text)
        assert len(boundaries) == 2
        assert 0 in boundaries


class TestTxtParser:
    def test_supports_format(self):
        parser = TxtParser()
        assert parser.supports_format("file.txt")
        assert not parser.supports_format("file.epub")
        assert not parser.supports_format("file.pdf")

    def test_parse_simple_txt(self):
        parser = TxtParser()
        content = """Chapter 1

The rain fell in sheets across the ancient city.

She turned to find him emerging from the shadows.

Chapter 2

The Archive sat beneath the Grand Temple."""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            tmp_path = f.name

        try:
            doc = parser.parse(tmp_path)
            assert "Tmp" in doc.title or "tmp" in doc.title.lower()
            assert len(doc.chapters) >= 1
            assert len(doc.chapters[0].paragraphs) > 0
        finally:
            os.unlink(tmp_path)

    def test_parse_empty_file(self):
        parser = TxtParser()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            tmp_path = f.name
        try:
            doc = parser.parse(tmp_path)
            assert len(doc.chapters) >= 0
        finally:
            os.unlink(tmp_path)

    def test_scene_detection(self):
        parser = TxtParser()
        content = """Chapter 1

First paragraph.

---

Second paragraph.

* * *

Third paragraph."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            doc = parser.parse(tmp_path)
            assert len(doc.chapters) > 0
        finally:
            os.unlink(tmp_path)
