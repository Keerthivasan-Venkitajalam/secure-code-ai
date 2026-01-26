"""
SecureCodeAI - Logging Configuration
Structured JSON logging with loguru for observability and debugging.
"""

import sys
import json
from typing import Dict, Any, Optional
from contextvars import ContextVar
from loguru import logger

from .config import config


# Context variable for request-scoped data
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


def serialize_log_record(record: Dict[str, Any]) -> str:
    """
    Serialize log record to JSON format.
    
    Args:
        record: Loguru log record
        
    Returns:
        JSON-formatted log string
    """
    # Extract context from ContextVar
    context = request_context.get()
    
    # Build structured log entry
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add request context if available
    if context:
        log_entry["context"] = context
    
    # Add exception info if present
    if record["exception"]:
        exc_type = record["exception"].type
        exc_value = record["exception"].value
        
        log_entry["exception"] = {
            "type": exc_type.__name__ if hasattr(exc_type, '__name__') else str(exc_type),
            "value": str(exc_value),
            "traceback": str(record["exception"].traceback) if record["exception"].traceback else None
        }
    
    # Add extra fields from record
    if record.get("extra"):
        for key, value in record["extra"].items():
            if key not in log_entry:
                # Ensure value is JSON serializable
                try:
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)
    
    return json.dumps(log_entry)


def configure_logging() -> None:
    """
    Configure loguru for structured JSON logging.
    
    Sets up:
    - JSON format for production
    - Human-readable format for development
    - Log level from configuration
    - Request context tracking
    """
    # Remove default handler
    logger.remove()
    
    # Determine log format based on environment
    # Use human-readable format for all environments to avoid JSON serialization issues
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stderr,
        format=log_format,
        level=config.log_level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    logger.info(f"Logging configured with level: {config.log_level.upper()}")


def set_request_context(
    request_id: Optional[str] = None,
    code_length: Optional[int] = None,
    file_path: Optional[str] = None,
    **kwargs
) -> None:
    """
    Set request-scoped context for logging.
    
    Args:
        request_id: Unique request identifier
        code_length: Length of code being analyzed
        file_path: File path being analyzed
        **kwargs: Additional context fields
    """
    context = {}
    
    if request_id:
        context["request_id"] = request_id
    if code_length is not None:
        context["code_length"] = code_length
    if file_path:
        context["file_path"] = file_path
    
    # Add any additional context
    context.update(kwargs)
    
    request_context.set(context)


def clear_request_context() -> None:
    """Clear request-scoped context."""
    request_context.set({})


def get_request_context() -> Dict[str, Any]:
    """Get current request context."""
    return request_context.get()


# Export configured logger
__all__ = [
    "logger",
    "configure_logging",
    "set_request_context",
    "clear_request_context",
    "get_request_context"
]
