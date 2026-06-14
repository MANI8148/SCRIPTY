from typing import List, Optional
from pathlib import Path
import logging
from data_pipeline.parsers.base_parser import ParsedDocument
from data_pipeline.parsers.txt_parser import TxtParser
from data_pipeline.parsers.epub_parser import EpubParser
from data_pipeline.parsers.pdf_parser import PdfParser


logger = logging.getLogger(__name__)


class StructuralParsingPass:
    def __init__(self):
        self.parsers = [TxtParser(), EpubParser(), PdfParser()]

    def execute(self, file_paths: List[str]) -> List[ParsedDocument]:
        documents = []
        for fp in file_paths:
            try:
                doc = self._parse_file(fp)
                if doc:
                    documents.append(doc)
                    logger.info(f"Parsed: {fp} -> {len(doc.chapters)} chapters")
            except Exception as e:
                logger.error(f"Failed to parse {fp}: {e}")
        return documents

    def _parse_file(self, file_path: str) -> Optional[ParsedDocument]:
        for parser in self.parsers:
            if parser.supports_format(file_path):
                return parser.parse(file_path)
        logger.warning(f"No parser found for: {file_path}")
        return None

    def get_supported_extensions(self) -> List[str]:
        return ['.txt', '.epub', '.pdf']

    def discover_files(self, input_dir: str, recursive: bool = True) -> List[str]:
        path = Path(input_dir)
        files = []
        for ext in self.get_supported_extensions():
            pattern = f"**/*{ext}" if recursive else f"*{ext}"
            files.extend(str(p) for p in path.glob(pattern))
        return sorted(files)
