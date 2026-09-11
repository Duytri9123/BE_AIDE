"""
Logging configuration với structured logging support
"""
import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter cho structured logging
    Output: {"timestamp": "...", "level": "...", "logger": "...", "message": "...", "extra": {...}}
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        else:
            # Capture any custom attributes
            extra = {}
            for key, value in record.__dict__.items():
                if key not in [
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "message", "pathname", "process", "processName",
                    "relativeCreated", "thread", "threadName", "exc_info",
                    "exc_text", "stack_info", "getMessage", "extra"
                ]:
                    extra[key] = value
            
            if extra:
                log_data["extra"] = extra
        
        # Add source location
        log_data["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName
        }
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """
    Standard text formatter với colors (if terminal supports)
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        # Base format
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()
        
        # Add color if enabled
        if self.use_colors:
            color = self.COLORS.get(level, '')
            reset = self.COLORS['RESET']
            level = f"{color}{level}{reset}"
        
        # Format
        log_line = f"[{timestamp}] {level:20} {logger_name:30} {message}"
        
        # Add exception if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        
        return log_line


def setup_logging():
    """
    Setup logging configuration based on settings
    """
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Choose formatter based on config
    if settings.LOG_FORMAT.lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(TextFormatter(use_colors=True))
    
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    if settings.LOG_FILE:
        log_file_path = Path(settings.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Always use JSON for file logs
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Application loggers - more verbose
    logging.getLogger("app").setLevel(logging.DEBUG)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "level": settings.LOG_LEVEL,
            "format": settings.LOG_FORMAT,
            "log_file": settings.LOG_FILE
        }
    )


# Context manager for adding extra context to logs
class LogContext:
    """
    Context manager để thêm extra fields vào logs
    
    Usage:
        with LogContext(request_id="123", user_id=456):
            logger.info("Processing request")
            # Output includes request_id and user_id
    """
    
    _context_stack = []
    
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        LogContext._context_stack.append(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        LogContext._context_stack.pop()
    
    @classmethod
    def get_current_context(cls) -> dict:
        """Get merged context from all active LogContext instances"""
        merged = {}
        for ctx in cls._context_stack:
            merged.update(ctx)
        return merged


# Custom logger adapter that adds context
class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds context from LogContext
    """
    
    def process(self, msg, kwargs):
        # Get current context
        context = LogContext.get_current_context()
        
        # Merge with any extra passed in kwargs
        if "extra" in kwargs:
            context.update(kwargs["extra"])
        
        if context:
            kwargs["extra"] = context
        
        return msg, kwargs


def get_logger(name: str) -> ContextLogger:
    """
    Get a logger with context support
    
    Usage:
        logger = get_logger(__name__)
        with LogContext(project_id=123):
            logger.info("Processing project")  # Automatically includes project_id
    """
    base_logger = logging.getLogger(name)
    return ContextLogger(base_logger, {})


# Convenience function for structured logging
def log_event(
    logger: logging.Logger,
    level: str,
    event_name: str,
    message: str = "",
    **kwargs
):
    """
    Log a structured event
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        event_name: Event identifier (e.g., "device_extracted", "ai_call_failed")
        message: Human-readable message
        **kwargs: Additional structured data
    
    Example:
        log_event(
            logger,
            "info",
            "device_extracted",
            "Successfully extracted device",
            device_type="MCCB",
            current=630,
            confidence=0.95
        )
    """
    log_method = getattr(logger, level.lower())
    log_method(
        f"[{event_name}] {message}" if message else f"[{event_name}]",
        extra={"event": event_name, **kwargs}
    )
