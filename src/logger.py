"""
Logging configuration for the URL scraper project.
Uses a single JSON file for all logs with append mode.
"""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class JSONFileHandler(logging.FileHandler):
    """File handler that appends JSON logs to a single file."""
    
    def emit(self, record):
        """Emit a log record as a JSON line."""
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + '\n')
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logger(name: str, log_dir: Path) -> logging.Logger:
    """
    Set up a logger with JSON file handler and console handler.
    
    Args:
        name: Name of the logger
        log_dir: Directory to store log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent adding handlers multiple times
    if logger.handlers:
        return logger
    
    # JSON formatter for file
    json_formatter = JSONFormatter()
    
    # Console formatter (human-readable)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler - single JSON file with append mode
    log_file = log_dir / "scraper.log"
    file_handler = JSONFileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_formatter)
    
    # Console handler - logs INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger