import logging
import sys
import structlog
from structlog.types import Processor
from typing import Any

from .config import settings

# Set of keys to automatically mask in logs
# Expand this list as needed
SENSITIVE_KEYS = {
    "password", "tufin_password", "api_key", "x-api-key", 
    "authorization", "secret", "token"
    # Add keys from request/response bodies if they contain sensitive info
}

# Recursive masking function
def _mask_dict(data: Any) -> Any:
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if isinstance(k, str) and k.lower() in SENSITIVE_KEYS:
                new_dict[k] = "***MASKED***"
            else:
                new_dict[k] = _mask_dict(v)
        return new_dict
    elif isinstance(data, list):
        return [_mask_dict(item) for item in data]
    # Add handling for other types if necessary
    return data

def mask_sensitive_processor(logger, method_name, event_dict):
    """Structlog processor to mask sensitive keys recursively."""
    # Check common keys in the main event dict
    for key in list(event_dict.keys()): # Iterate over keys copy
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "***MASKED***"
            
    # Recursively check nested structures (e.g., request/response bodies if logged)
    # Note: This assumes sensitive data might be directly in the event_dict.
    # If sensitive data is logged structured within specific keys (e.g., event_dict['http_response']), 
    # you might need to target those specifically.
    # Example: if 'http_request_body' in event_dict:
    #             event_dict['http_request_body'] = _mask_dict(event_dict['http_request_body'])
            
    # Basic check for common sensitive headers often put in context
    # This is limited, more robust header masking might be needed in middleware
    if "headers" in event_dict and isinstance(event_dict["headers"], dict):
         for h_key in list(event_dict["headers"].keys()):
             if h_key.lower() in SENSITIVE_KEYS:
                 event_dict["headers"][h_key] = "***MASKED***"
                 
    return event_dict

def add_request_id(logger, method_name, event_dict):
    """Structlog processor to add request_id if it exists in context vars."""
    # Requires contextvars to be set, typically by middleware
    try:
        from structlog.contextvars import get_contextvars
        context = get_contextvars()
        request_id = context.get("request_id")
        if request_id:
            event_dict["request_id"] = request_id
    except ImportError:
        pass # Contextvars might not be available or needed in all contexts
    return event_dict

def setup_logging():
    """Configures structlog for structured JSON logging."""
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars, # Get context like request_id
        add_request_id, # Add request_id specifically if present
        mask_sensitive_processor, # Add the masking processor here
        structlog.stdlib.add_logger_name, # Adds logger name (e.g., module)
        structlog.stdlib.add_log_level, # Adds log level (e.g., info, error)
        structlog.processors.TimeStamper(fmt="iso"), # ISO 8601 timestamp
        structlog.processors.format_exc_info, # Formats exception info
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Define formatter for standard library handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        # These processors are applied only at the very end
        processor=structlog.processors.JSONRenderer(),
        # Keep log records clean for the final renderer
        foreign_pre_chain=shared_processors,
    )

    # Configure standard logging handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Configure uvicorn loggers to use our handler
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        log = logging.getLogger(logger_name)
        log.handlers = [handler]
        log.propagate = False # Prevent double logging by root logger

    print(f"Structured logging configured at level: {settings.LOG_LEVEL}")

# Call setup on import (or call explicitly in main.py before app creation)
# setup_logging() 