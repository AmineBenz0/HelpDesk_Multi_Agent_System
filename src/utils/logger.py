# src/utils/logger.py
import logging
from datetime import datetime
from typing import Optional
from config.settings import settings

class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for logs"""
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[91m', # Red
        'RESET': '\033[0m'     # Reset
    }

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        message = super().format(record)
        return f"{level_color}{message}{self.COLORS['RESET']}"

def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger(name or __name__)
    logger.setLevel(logging.DEBUG if settings.DEBUG_MODE else logging.INFO)
    
    if not logger.handlers:
        ch = logging.StreamHandler()
        formatter = ColoredFormatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    
    return logger

logger = setup_logger()