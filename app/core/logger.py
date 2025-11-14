"""Secure logging configuration without PII leaks."""

import logging
import re
import sys
from typing import Any, Dict, Optional
from pathlib import Path

from .config import settings


class PIISafeFormatter(logging.Formatter):
    """Custom formatter that removes PII from log messages."""
    
    # Patterns to redact sensitive information
    REDACT_PATTERNS = [
        (re.compile(r'\b\d{10}:\w{35}\b'), '[BOT_TOKEN]'),  # Bot token pattern
        (re.compile(r'\b[A-Za-z0-9]{32,}\b'), '[API_KEY]'),  # API keys
        (re.compile(r'\b\d{8,12}\b'), '[USER_ID]'),  # User IDs
        (re.compile(r'@\w+'), '[USERNAME]'),  # Usernames
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),  # Emails
        (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP]'),  # IP addresses
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII redaction."""
        # Format the original message
        formatted = super().format(record)
        
        # Apply redaction patterns
        for pattern, replacement in self.REDACT_PATTERNS:
            formatted = pattern.sub(replacement, formatted)
        
        return formatted


def setup_logging() -> logging.Logger:
    """Setup secure logging configuration."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger("telegram_translator")
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = PIISafeFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_dir / "bot.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.FileHandler(log_dir / "error.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # Disable propagation to avoid duplicate logs
    logger.propagate = False
    
    # Configure third-party loggers
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"telegram_translator.{name}")


def log_safe_dict(data: Dict[str, Any], exclude_keys: Optional[set] = None) -> Dict[str, Any]:
    """Create a safe dictionary for logging by excluding sensitive keys."""
    if exclude_keys is None:
        exclude_keys = {
            'token', 'api_key', 'password', 'secret', 'key', 
            'authorization', 'auth', 'credentials', 'private'
        }
    
    safe_data = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in exclude_keys):
            safe_data[key] = '[REDACTED]'
        elif isinstance(value, dict):
            safe_data[key] = log_safe_dict(value, exclude_keys)
        else:
            safe_data[key] = value
    
    return safe_data


# Initialize logger
logger = setup_logging()

