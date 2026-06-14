import os
from pathlib import Path
from typing import List, Optional

from data_pipeline.schema.taxonomy import Category


ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = ROOT.parent

DEFAULT_PIPELINE_CONFIG = {
    "input_dir": str(PROJECT_ROOT / "data" / "gutenberg"),
    "output_dir": str(PROJECT_ROOT / "data_pipeline" / "output"),
    "cache_dir": str(PROJECT_ROOT / "data_pipeline" / "cache"),
    "report_dir": str(PROJECT_ROOT / "data_pipeline" / "reports"),
    "fragment_store": str(PROJECT_ROOT / "data_pipeline" / "output" / "fragments.jsonl"),
    "elite_store": str(PROJECT_ROOT / "data_pipeline" / "output" / "elite_fragments.jsonl"),
    "character_memory_store": str(PROJECT_ROOT / "data_pipeline" / "output" / "character_memory_fragments.jsonl"),
    "foreshadowing_graph": str(PROJECT_ROOT / "data_pipeline" / "output" / "foreshadowing_graph.json"),
    "scene_blueprints": str(PROJECT_ROOT / "data_pipeline" / "output" / "scene_blueprints.jsonl"),
    "faiss_index_path": str(PROJECT_ROOT / "data_pipeline" / "output" / "faiss_index"),
    "corpus_jsonl": str(PROJECT_ROOT / "data_pipeline" / "output" / "rag_corpus.jsonl"),
}

EXTRACTION_CONFIG = {
    "min_paragraph_length": 20,
    "max_paragraph_length": 2000,
    "chunk_size": 5,
    "overlap": 1,
    "min_sentence_length": 10,
    "max_sentences_per_fragment": 8,
    "dialogue_patterns": [
        r'["\u201C][^"\u201D]+["\u201D]',
        r'["\u2018][^"\u2019]+["\u2019]',
        r"'[^']+'",
    ],
    "body_language_indicators": [
        "crossed his arms", "crossed her arms",
        "raised an eyebrow", "rolled his eyes", "rolled her eyes",
        "clenched his fist", "clenched her fist",
        "bowed his head", "bowed her head",
        "shook his head", "shook her head",
        "nodded", "shrugged", "smiled", "frowned", "grinned",
        "trembled", "shivered", "flinched", "recoiled", "stiffened",
        "leaned forward", "leaned back", "stepped closer",
        "paced", "fidgeted", "drummed", "tapped",
    ],
    "emotion_indicators": {
        "anger": ["angry", "furious", "rage", "frustrat", "enraged", "irate", "seething", "livid"],
        "fear": ["fear", "afraid", "scared", "terrified", "panicked", "dread", "horror", "anxious"],
        "joy": ["happy", "joy", "delight", "elated", "ecstatic", "thrilled", "pleased", "glee"],
        "sadness": ["sad", "grief", "sorrow", "melancholy", "despair", "heartbroken", "mourn", "weep"],
        "guilt": ["guilt", "remorse", "contrite", "regret", "culpable", "blame"],
        "shame": ["shame", "humiliat", "embarrass", "mortified", "disgrace"],
        "jealousy": ["jealous", "envy", "covet", "resentful", "possessive"],
        "hope": ["hope", "optimis", "aspire", "confident", "wishful", "eager"],
        "desperation": ["desperate", "frantic", "anguish", "despair", "hopeless", "futile"],
    },
    "conflict_indicators": {
        "internal": ["struggl", "wrestl", "conflict", "doubt", "question", "uncertain", "debate within", "war within"],
        "interpersonal": ["argu", "fight", "disagree", "quarrel", "shout", "yell", "accus", "blame"],
        "group": ["faction", "group", "team", "divided", "split", "fracture", "alliance"],
        "institutional": ["system", "institution", "government", "law", "authority", "bureau", "society"],
        "moral": ["moral", "ethic", "conscience", "right", "wrong", "principle", "dilemma", "virtue"],
    },
    "sensory_indicators": {
        "visual": ["saw", "looked", "watched", "gazed", "glanced", "observed", "noticed", "seen", "view", "appear"],
        "auditory": ["heard", "listened", "sound", "voice", "whisper", "scream", "crash", "bang", "footstep", "melody"],
        "olfactory": ["smell", "scent", "aroma", "fragrance", "stench", "odor", "reek", "perfume", "stink"],
        "tactile": ["felt", "touch", "texture", "smooth", "rough", "warm", "cold", "soft", "hard", "pressure"],
        "gustatory": ["taste", "flavor", "bitter", "sweet", "sour", "salty", "savory", "delicious"],
    },
    "scene_boundary_indicators": [
        "chapter", "CHAPTER",
        "---", "***",
        "Part ", "BOOK ",
        "one day later", "the next day", "meanwhile",
        "later that", "hours passed",
    ],
    "narrative_device_indicators": {
        "foreshadowing": ["little did", "would later", "omen", "premonition", "foreboding", "portent", "harbinger"],
        "setup": ["if only", "had he known", "what he didn't know", "unaware", "unknowingly"],
        "payoff": ["as it turned out", "now he understood", "finally realized", "in the end"],
        "symbolism": ["symboliz", "represent", "embody", "signify", "metaphor"],
    },
}

QUALITY_CONFIG = {
    "min_quality_score": 0.60,
    "elite_threshold": 0.85,
    "weights": {
        "literary_quality": 0.15,
        "specificity": 0.15,
        "emotion_clarity": 0.15,
        "dialogue_quality": 0.15,
        "imagery_quality": 0.15,
        "sensory_density": 0.10,
        "uniqueness": 0.05,
        "reusability": 0.10,
    },
}

DEDUP_CONFIG = {
    "model_name": "all-MiniLM-L6-v2",
    "duplicate_threshold": 0.90,
    "near_duplicate_threshold": 0.80,
    "batch_size": 512,
}

RAG_CONFIG = {
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dim": 384,
    "faiss_index_type": "Flat",
    "batch_size": 256,
}

PASSES = [
    "structural_parsing",
    "narrative_fragment_extraction",
    "character_extraction",
    "relationship_extraction",
    "emotion_extraction",
    "conflict_extraction",
    "narrative_device_extraction",
    "worldbuilding_extraction",
    "scene_pattern_extraction",
    "genre_pattern_extraction",
]

GENRE_MAP = {
    "mystery": Category.MYSTERY,
    "thriller": Category.THRILLER,
    "romance": Category.ROMANCE,
    "fantasy": Category.FANTASY,
    "science_fiction": Category.SCIENCE_FICTION,
    "literary": Category.LITERARY,
    "historical": Category.HISTORICAL,
    "horror": Category.HORROR,
}
