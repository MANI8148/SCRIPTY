"""
SCRIPTY - Configuration Module
Reads environment variables with sensible defaults
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _safe_int(value: str | None, default: int) -> int:
    """Parse an integer from a string, returning default on failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default


class Config:
    """Application configuration with environment variable support"""
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Cache Configuration
    CACHE_TTL_HOURS = _safe_int(os.getenv("CACHE_TTL_HOURS", "24"), 24)
    
    # API Configuration
    API_TIMEOUT_SECONDS = _safe_int(os.getenv("API_TIMEOUT_SECONDS", "3"), 3)
    
    # Entity Validation
    ENTITY_VALIDATION_STRICT = os.getenv("ENTITY_VALIDATION_STRICT", "true").lower() == "true"
    
    # Server Configuration
    PORT = _safe_int(os.getenv("PORT", "5000"), 5000)
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # Research pipeline configuration
    RAG_BACKEND = os.getenv("RAG_BACKEND", "tfidf")
    RAG_TOP_K = _safe_int(os.getenv("RAG_TOP_K", "5"), 5)
    WORKING_MEMORY_CAPACITY = _safe_int(os.getenv("WORKING_MEMORY_CAPACITY", "3"), 3)
    RESEARCH_OUTPUT_DIR = os.getenv("RESEARCH_OUTPUT_DIR", "backend/research_output")
    LLM_ADAPTER_ENABLED = os.getenv("LLM_ADAPTER_ENABLED", "false").lower() == "true"
    LLM_ADAPTER_ENDPOINT = os.getenv("LLM_ADAPTER_ENDPOINT", "http://127.0.0.1:11434/api/generate")
    # "tfidf" enables lazy TF-IDF cosine similarity for SemanticMemory.retrieve_similar;
    # "none" falls back to substring matching only.
    SEMANTIC_VECTOR_BACKEND = os.getenv("SEMANTIC_VECTOR_BACKEND", "none")
    SCRIPTY_PHASE_A_ENABLED = os.getenv("SCRIPTY_PHASE_A_ENABLED", "true").lower() == "true"
    SCRIPTY_PHASE_B_ENABLED = os.getenv("SCRIPTY_PHASE_B_ENABLED", "true").lower() == "true"
    SCRIPTY_PHASE_C_ENABLED = os.getenv("SCRIPTY_PHASE_C_ENABLED", "true").lower() == "true"
    SCRIPTY_BACKWARD_COMPATIBILITY_MODE = os.getenv("SCRIPTY_BACKWARD_COMPATIBILITY_MODE", "false").lower() == "true"
    SCRIPTY_VECTOR_BACKEND = os.getenv("SCRIPTY_VECTOR_BACKEND", "local")
    SCRIPTY_EMBEDDING_MODEL = os.getenv("SCRIPTY_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    SCRIPTY_SCENE_PREDICTOR = os.getenv("SCRIPTY_SCENE_PREDICTOR", "random_forest")
    SCRIPTY_MEMORY_TOP_K = _safe_int(os.getenv("SCRIPTY_MEMORY_TOP_K", "5"), 5)
    SCRIPTY_OUTPUT_DASHBOARD = os.getenv("SCRIPTY_OUTPUT_DASHBOARD", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate configuration on startup and log warnings for missing optional variables"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Validate required variables
        if os.getenv("REDIS_URL") is None:
            logger.warning("REDIS_URL not set, using default: redis://localhost:6379/0")
        
        # Validate numeric ranges
        if cls.CACHE_TTL_HOURS < 1:
            logger.warning(f"CACHE_TTL_HOURS={cls.CACHE_TTL_HOURS} is too low, using default: 24")
            cls.CACHE_TTL_HOURS = 24
        
        if cls.API_TIMEOUT_SECONDS < 1:
            logger.warning(f"API_TIMEOUT_SECONDS={cls.API_TIMEOUT_SECONDS} is too low, using default: 3")
            cls.API_TIMEOUT_SECONDS = 3
        if cls.RAG_TOP_K < 1:
            logger.warning(f"RAG_TOP_K={cls.RAG_TOP_K} is too low, using default: 5")
            cls.RAG_TOP_K = 5
        if cls.WORKING_MEMORY_CAPACITY < 1:
            logger.warning(f"WORKING_MEMORY_CAPACITY={cls.WORKING_MEMORY_CAPACITY} is too low, using default: 3")
            cls.WORKING_MEMORY_CAPACITY = 3
        if cls.SCRIPTY_MEMORY_TOP_K < 1:
            logger.warning(f"SCRIPTY_MEMORY_TOP_K={cls.SCRIPTY_MEMORY_TOP_K} is too low, using default: 5")
            cls.SCRIPTY_MEMORY_TOP_K = 5
        
        if not (1024 <= cls.PORT <= 65535):
            logger.warning(f"PORT={cls.PORT} is invalid, using default: 5000")
            cls.PORT = 5000
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_log_levels:
            logger.warning(f"LOG_LEVEL={cls.LOG_LEVEL} is invalid, using default: INFO")
            cls.LOG_LEVEL = "INFO"
        
        logger.info("Configuration validated successfully")
        logger.info(f"Redis URL: {cls.REDIS_URL}")
        logger.info(f"Cache TTL: {cls.CACHE_TTL_HOURS} hours")
        logger.info(f"API Timeout: {cls.API_TIMEOUT_SECONDS} seconds")
        logger.info(f"Entity Validation Strict: {cls.ENTITY_VALIDATION_STRICT}")
        logger.info(f"Server Port: {cls.PORT}")
        logger.info(f"Log Level: {cls.LOG_LEVEL}")


# Create singleton config instance
config = Config()
