from typing import List, Optional
from .base_parser import BaseParser, ParsedDocument, ParsedChapter, ParsedScene
import re


try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    HAS_EPUB = True
except ImportError:
    HAS_EPUB = False


class EpubParser(BaseParser):
    def supports_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.epub')

    def parse(self, file_path: str) -> ParsedDocument:
        if not HAS_EPUB:
            raise ImportError("ebooklib required for EPUB parsing. Install: pip install ebooklib beautifulsoup4")

        book = epub.read_epub(file_path)
        title = book.get_metadata('DC', 'title')
        title = title[0][0] if title else self.extract_title_from_path(file_path)

        author = book.get_metadata('DC', 'creator')
        author = author[0][0] if author else ""

        doc = ParsedDocument(source_path=file_path, title=title, author=author)
        chapter_num = 0

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)

                if len(text) < 50:
                    continue

                chapter_num += 1
                lines = text.split('\n')
                paragraphs = [l.strip() for l in lines if len(l.strip()) > 20]
                chapter = ParsedChapter(number=chapter_num, paragraphs=paragraphs)

                scene_boundaries = self.detect_scene_boundaries(paragraphs)
                for si in range(len(scene_boundaries) - 1):
                    s_start = scene_boundaries[si]
                    s_end = scene_boundaries[si + 1]
                    scene_paras = paragraphs[s_start:s_end]
                    if scene_paras:
                        scene = ParsedScene(number=si + 1, paragraphs=scene_paras)
                        chapter.scenes.append(scene)

                doc.chapters.append(chapter)

        return doc
