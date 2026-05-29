"""
SCRIPTY - Structured JSON Logging Configuration
Provides structured logging with JSON format for production observability
"""
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in structured JSON format"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "location"):
            log_data["location"] = record.location
        
        if hasattr(record, "year"):
            log_data["year"] = record.year
        
        if hasattr(record, "generation_time_ms"):
            log_data["generation_time_ms"] = record.generation_time_ms
        
        if hasattr(record, "cache_key"):
            log_data["cache_key"] = record.cache_key
        
        if hasattr(record, "cache_operation"):
            log_data["cache_operation"] = record.cache_operation
        
        if hasattr(record, "operation_time_ms"):
            log_data["operation_time_ms"] = record.operation_time_ms
        
        if hasattr(record, "api_endpoint"):
            log_data["api_endpoint"] = record.api_endpoint
        
        if hasattr(record, "response_time_ms"):
            log_data["response_time_ms"] = record.response_time_ms
        
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        if hasattr(record, "entity_name"):
            log_data["entity_name"] = record.entity_name
        
        if hasattr(record, "rejection_reason"):
            log_data["rejection_reason"] = record.rejection_reason
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["stack_trace"] = self.formatStack(record.stack_info) if record.stack_info else None
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(JSONFormatter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set log level for third-party libraries to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding extra fields to log records"""
    
    def __init__(self, logger: logging.Logger, **kwargs):
        """
        Initialize log context
        
        Args:
            logger: Logger instance
            **kwargs: Extra fields to add to log records
        """
        self.logger = logger
        self.extra_fields = kwargs
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and add extra fields"""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.extra_fields.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory"""
        logging.setLogRecordFactory(self.old_factory)
