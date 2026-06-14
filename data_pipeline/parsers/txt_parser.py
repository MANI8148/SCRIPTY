from typing import List, Optional
from .base_parser import BaseParser, ParsedDocument, ParsedChapter, ParsedScene


class TxtParser(BaseParser):
    def supports_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.txt')

    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()

        title = self.extract_title_from_path(file_path)
        doc = ParsedDocument(source_path=file_path, title=title)

        chapter_boundaries = self.detect_chapter_boundaries(text)
        lines = text.split('\n')

        chapter_boundaries.append(len(lines))

        for ci in range(len(chapter_boundaries) - 1):
            start = chapter_boundaries[ci]
            end = chapter_boundaries[ci + 1]
            chapter_lines = lines[start:end]
            chapter_title = chapter_lines[0].strip() if chapter_lines else ""
            chapter_number = ci + 1

            paragraphs = []
            current = []
            for line in chapter_lines[1:]:
                stripped = line.strip()
                if not stripped:
                    if current:
                        paragraphs.append(' '.join(current))
                        current = []
                else:
                    current.append(stripped)
            if current:
                paragraphs.append(' '.join(current))

            chapter = ParsedChapter(
                number=chapter_number,
                title=chapter_title,
                paragraphs=paragraphs,
            )

            scene_boundaries = self.detect_scene_boundaries(paragraphs)
            for si in range(len(scene_boundaries) - 1):
                s_start = scene_boundaries[si]
                s_end = scene_boundaries[si + 1]
                scene_paras = paragraphs[s_start:s_end]
                if scene_paras:
                    scene = ParsedScene(
                        number=si + 1,
                        paragraphs=scene_paras,
                        start_line=s_start,
                        end_line=s_end,
                    )
                    chapter.scenes.append(scene)

            doc.chapters.append(chapter)

        return doc
