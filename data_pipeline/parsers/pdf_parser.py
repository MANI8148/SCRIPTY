from typing import List, Optional
from .base_parser import BaseParser, ParsedDocument, ParsedChapter, ParsedScene


try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class PdfParser(BaseParser):
    def supports_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.pdf')

    def parse(self, file_path: str) -> ParsedDocument:
        title = self.extract_title_from_path(file_path)
        doc = ParsedDocument(source_path=file_path, title=title)

        if HAS_PDFPLUMBER:
            return self._parse_with_pdfplumber(file_path, doc)
        elif HAS_PYPDF2:
            return self._parse_with_pypdf2(file_path, doc)
        else:
            raise ImportError("PDF parsing requires pdfplumber or PyPDF2. Install: pip install pdfplumber or PyPDF2")

    def _parse_with_pdfplumber(self, file_path: str, doc: ParsedDocument) -> ParsedDocument:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = '\n'.join(all_text)
        return self._build_document(full_text, doc)

    def _parse_with_pypdf2(self, file_path: str, doc: ParsedDocument) -> ParsedDocument:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            all_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        full_text = '\n'.join(all_text)
        return self._build_document(full_text, doc)

    def _build_document(self, full_text: str, doc: ParsedDocument) -> ParsedDocument:
        chapter_boundaries = self.detect_chapter_boundaries(full_text)
        lines = full_text.split('\n')
        chapter_boundaries.append(len(lines))

        for ci in range(len(chapter_boundaries) - 1):
            start = chapter_boundaries[ci]
            end = chapter_boundaries[ci + 1]
            chapter_lines = lines[start:end]
            chapter_number = ci + 1

            paragraphs = []
            current = []
            for line in chapter_lines:
                stripped = line.strip()
                if not stripped:
                    if current:
                        paragraphs.append(' '.join(current))
                        current = []
                else:
                    current.append(stripped)
            if current:
                paragraphs.append(' '.join(current))

            chapter = ParsedChapter(number=chapter_number, paragraphs=paragraphs)

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
