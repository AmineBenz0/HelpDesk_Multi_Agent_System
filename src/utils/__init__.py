# src/utils/__init__.py
"""
Utility functions and helpers for the Helpdesk system.

Includes:
- logger: Custom logging configuration
- prompts: Prompt templates and management
- document_parser: Document processing pipeline
"""

from .logger import logger, setup_logger
from .prompts import get_email_classification_prompt, get_prompt
from .document_parser import DocumentProcessor

__all__ = [
    'logger',
    'setup_logger',
    'get_email_classification_prompt',
    'get_prompt',
    'DocumentProcessor'
]