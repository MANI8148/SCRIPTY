"""
SCRIPTY - Book Exporter
Handles export of generated books in multiple formats: plain text, markdown, and JSON.

This module provides the BookExporter class which converts the internal book
representation (chapters, scenes, metadata) into human-readable and
machine-readable export formats.

Requirements: 14.6, 14.7, 15.10
"""
import json
from dataclasses import asdict
from datetime import datetime
from typing import Optional

try:
    from backend.core.data_models import BookMetadata, Chapter, Scene
    from backend.utils.logging_config import get_logger
except ImportError:
    from core.data_models import BookMetadata, Chapter, Scene
    from utils.logging_config import get_logger

logger = get_logger(__name__)


class BookExporter:
    """
    Exports generated books in plain text, markdown, and JSON formats.

    Supports three export formats:
    - Plain text (.txt): Human-readable, no markup
    - Markdown (.md): Formatted with headers and structure
    - JSON (.json): Structured data with all metadata and scene details

    Requirements: 14.6, 14.7, 15.10
    """

    # Average adult reading speed in words per minute
    READING_SPEED_WPM = 200

    # ------------------------------------------------------------------ #
    # Metadata helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_word_count(
        prologue: Optional[str],
        chapters: list[Chapter],
        epilogue: Optional[str],
    ) -> int:
        """
        Calculate total word count across prologue, chapters, and epilogue.

        Args:
            prologue: Optional prologue text
            chapters: List of Chapter objects
            epilogue: Optional epilogue text

        Returns:
            Total word count as an integer

        Requirements: 14.6
        """
        total = 0
        if prologue:
            total += len(prologue.split())
        for chapter in chapters:
            total += chapter.word_count
        if epilogue:
            total += len(epilogue.split())
        logger.debug("Word count calculated", extra={"total_word_count": total})
        return total

    @staticmethod
    def calculate_reading_time(total_word_count: int) -> int:
        """
        Estimate reading time in minutes based on word count.

        Uses an average adult reading speed of 200 words per minute.

        Args:
            total_word_count: Total number of words in the book

        Returns:
            Estimated reading time in minutes (minimum 1)

        Requirements: 14.6
        """
        reading_time = max(1, total_word_count // BookExporter.READING_SPEED_WPM)
        logger.debug(
            "Reading time calculated",
            extra={
                "total_word_count": total_word_count,
                "reading_time_minutes": reading_time,
            },
        )
        return reading_time

    @staticmethod
    def generate_table_of_contents(
        chapters: list[Chapter],
        include_prologue: bool = False,
        include_epilogue: bool = False,
    ) -> list[tuple[int, str]]:
        """
        Generate a table of contents with chapter numbers and titles.

        Entry numbering:
        - Prologue is entry 0 (if present)
        - Chapters are numbered 1..N
        - Epilogue is entry N+1 (if present)

        Args:
            chapters: List of Chapter objects
            include_prologue: Whether to include a Prologue entry
            include_epilogue: Whether to include an Epilogue entry

        Returns:
            List of (entry_number, title) tuples

        Requirements: 14.7
        """
        toc: list[tuple[int, str]] = []

        if include_prologue:
            toc.append((0, "Prologue"))

        for chapter in chapters:
            toc.append((chapter.chapter_num, chapter.title))

        if include_epilogue:
            epilogue_num = (chapters[-1].chapter_num + 1) if chapters else 1
            toc.append((epilogue_num, "Epilogue"))

        logger.debug(
            "Table of contents generated",
            extra={"entry_count": len(toc)},
        )
        return toc

    # ------------------------------------------------------------------ #
    # Export formats                                                       #
    # ------------------------------------------------------------------ #

    def export_plain_text(
        self,
        metadata: BookMetadata,
        chapters: list[Chapter],
        prologue: Optional[str] = None,
        epilogue: Optional[str] = None,
    ) -> str:
        """
        Export book as plain text.

        Structure:
        - Title block (title, author, genre, word count, reading time)
        - Table of contents
        - Prologue (if present)
        - Chapters with scenes
        - Epilogue (if present)

        Args:
            metadata: BookMetadata object
            chapters: List of Chapter objects
            prologue: Optional prologue text
            epilogue: Optional epilogue text

        Returns:
            Plain text string suitable for saving as .txt

        Requirements: 14.7
        """
        lines: list[str] = []

        # Title block
        lines.append(metadata.title.upper())
        lines.append("")
        lines.append(f"By: {metadata.author_attribution}")
        lines.append(f"Genre: {metadata.genre}")
        lines.append(f"Total words: {metadata.total_word_count:,}")
        lines.append(f"Estimated reading time: {metadata.reading_time_minutes} minutes")
        lines.append(
            f"Generated: {metadata.generation_timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

        # Table of contents
        lines.append("TABLE OF CONTENTS")
        lines.append("-" * 40)
        for entry_num, entry_title in metadata.table_of_contents:
            lines.append(f"  {entry_title}")
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

        # Prologue
        if prologue:
            lines.append(prologue)
            lines.append("")
            lines.append("=" * 60)
            lines.append("")

        # Chapters
        for chapter in chapters:
            lines.append(chapter.title.upper())
            lines.append("")
            for scene in chapter.scenes:
                lines.append(scene.content)
                lines.append("")
            lines.append(f"[Chapter word count: {chapter.word_count:,}]")
            lines.append("")
            lines.append("=" * 60)
            lines.append("")

        # Epilogue
        if epilogue:
            lines.append(epilogue)
            lines.append("")

        result = "\n".join(lines)
        logger.info(
            "Book exported as plain text",
            extra={
                "title": metadata.title,
                "char_count": len(result),
                "word_count": metadata.total_word_count,
            },
        )
        return result

    def export_markdown(
        self,
        metadata: BookMetadata,
        chapters: list[Chapter],
        prologue: Optional[str] = None,
        epilogue: Optional[str] = None,
    ) -> str:
        """
        Export book as Markdown.

        Structure:
        - H1 title with metadata block
        - Table of contents as a Markdown list
        - Prologue as H2 section (if present)
        - Chapters as H2 sections with H3 scene headings
        - Epilogue as H2 section (if present)

        Args:
            metadata: BookMetadata object
            chapters: List of Chapter objects
            prologue: Optional prologue text
            epilogue: Optional epilogue text

        Returns:
            Markdown string suitable for saving as .md

        Requirements: 14.7, 15.10
        """
        lines: list[str] = []

        # Title and metadata
        lines.append(f"# {metadata.title}")
        lines.append("")
        lines.append(f"**Author:** {metadata.author_attribution}  ")
        lines.append(f"**Genre:** {metadata.genre}  ")
        lines.append(f"**Total words:** {metadata.total_word_count:,}  ")
        lines.append(
            f"**Estimated reading time:** {metadata.reading_time_minutes} minutes  "
        )
        lines.append(
            f"**Generated:** "
            f"{metadata.generation_timestamp.strftime('%Y-%m-%d %H:%M UTC')}  "
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # Table of contents
        lines.append("## Table of Contents")
        lines.append("")
        for entry_num, entry_title in metadata.table_of_contents:
            # Create anchor link from title
            anchor = entry_title.lower().replace(" ", "-").replace(":", "").replace(",", "")
            lines.append(f"- [{entry_title}](#{anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Prologue
        if prologue:
            lines.append("## Prologue")
            lines.append("")
            # Preserve paragraph breaks
            for paragraph in prologue.split("\n\n"):
                stripped = paragraph.strip()
                if stripped and stripped.lower() != "prologue":
                    lines.append(stripped)
                    lines.append("")
            lines.append("---")
            lines.append("")

        # Chapters
        for chapter in chapters:
            lines.append(f"## {chapter.title}")
            lines.append("")
            for scene in chapter.scenes:
                lines.append(
                    f"### Scene {scene.scene_num} — {scene.scene_type.value.capitalize()}"
                )
                lines.append("")
                # Preserve paragraph breaks within scene content
                for paragraph in scene.content.split("\n\n"):
                    stripped = paragraph.strip()
                    if stripped:
                        lines.append(stripped)
                        lines.append("")
            lines.append(
                f"*Chapter word count: {chapter.word_count:,}*"
            )
            lines.append("")
            lines.append("---")
            lines.append("")

        # Epilogue
        if epilogue:
            lines.append("## Epilogue")
            lines.append("")
            for paragraph in epilogue.split("\n\n"):
                stripped = paragraph.strip()
                if stripped and stripped.lower() != "epilogue":
                    lines.append(stripped)
                    lines.append("")

        result = "\n".join(lines)
        logger.info(
            "Book exported as Markdown",
            extra={
                "title": metadata.title,
                "char_count": len(result),
                "word_count": metadata.total_word_count,
            },
        )
        return result

    def export_json(
        self,
        metadata: BookMetadata,
        chapters: list[Chapter],
        prologue: Optional[str] = None,
        epilogue: Optional[str] = None,
    ) -> str:
        """
        Export book as JSON with structured chapter and scene data.

        The JSON structure includes:
        - metadata: all BookMetadata fields
        - prologue: optional prologue text
        - chapters: list of chapters, each with scenes
        - epilogue: optional epilogue text

        Args:
            metadata: BookMetadata object
            chapters: List of Chapter objects
            prologue: Optional prologue text
            epilogue: Optional epilogue text

        Returns:
            JSON string suitable for saving as .json

        Requirements: 14.7
        """
        # Serialize metadata (convert datetime to ISO string)
        metadata_dict = {
            "title": metadata.title,
            "author_attribution": metadata.author_attribution,
            "genre": metadata.genre,
            "total_word_count": metadata.total_word_count,
            "chapter_count": metadata.chapter_count,
            "scene_count": metadata.scene_count,
            "reading_time_minutes": metadata.reading_time_minutes,
            "table_of_contents": [
                {"entry_num": num, "title": title}
                for num, title in metadata.table_of_contents
            ],
            "generation_timestamp": metadata.generation_timestamp.isoformat(),
        }

        # Serialize chapters and scenes
        chapters_list = []
        for chapter in chapters:
            scenes_list = [
                {
                    "scene_num": scene.scene_num,
                    "scene_type": scene.scene_type.value,
                    "content": scene.content,
                    "word_count": scene.word_count,
                }
                for scene in chapter.scenes
            ]
            chapters_list.append(
                {
                    "chapter_num": chapter.chapter_num,
                    "title": chapter.title,
                    "word_count": chapter.word_count,
                    "summary": chapter.summary,
                    "scenes": scenes_list,
                }
            )

        book_dict = {
            "metadata": metadata_dict,
            "prologue": prologue,
            "chapters": chapters_list,
            "epilogue": epilogue,
        }

        result = json.dumps(book_dict, ensure_ascii=False, indent=2)
        logger.info(
            "Book exported as JSON",
            extra={
                "title": metadata.title,
                "char_count": len(result),
                "word_count": metadata.total_word_count,
            },
        )
        return result

    def export(
        self,
        fmt: str,
        metadata: BookMetadata,
        chapters: list[Chapter],
        prologue: Optional[str] = None,
        epilogue: Optional[str] = None,
    ) -> str:
        """
        Export book in the specified format.

        Args:
            fmt: Export format — one of "txt", "md", "json"
            metadata: BookMetadata object
            chapters: List of Chapter objects
            prologue: Optional prologue text
            epilogue: Optional epilogue text

        Returns:
            Exported book as a string

        Raises:
            ValueError: If fmt is not one of the supported formats

        Requirements: 14.7
        """
        fmt = fmt.lower().strip()
        if fmt in ("txt", "text", "plain"):
            return self.export_plain_text(metadata, chapters, prologue, epilogue)
        elif fmt in ("md", "markdown"):
            return self.export_markdown(metadata, chapters, prologue, epilogue)
        elif fmt == "json":
            return self.export_json(metadata, chapters, prologue, epilogue)
        else:
            raise ValueError(
                f"Unsupported export format: '{fmt}'. "
                "Supported formats: 'txt', 'md', 'json'."
            )
