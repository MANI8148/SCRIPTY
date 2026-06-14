from typing import List, Optional
import logging
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.storage.faiss_index import FaissIndexBuilder
from data_pipeline.config import RAG_CONFIG


logger = logging.getLogger(__name__)


class IndexBuilder:
    def __init__(self, output_dir: str = None):
        self.config = RAG_CONFIG
        self.faiss_builder = FaissIndexBuilder(
            embedding_dim=self.config["embedding_dim"],
            index_type=self.config["faiss_index_type"],
        )
        self.output_dir = output_dir

    def build_and_save(self, fragments: List[NarrativeFragment], output_path: str) -> None:
        self.faiss_builder.build(fragments)
        self.faiss_builder.save(output_path)
        logger.info(f"Index saved to {output_path} ({self.faiss_builder.size} vectors)")
