# src/core/__init__.py
"""
Core components of the Helpdesk system.

Includes:
- GmailService: Handles Gmail API interactions
- LLMHandler: Manages LLM communications
"""

from .gmail_service import GmailService
from .llm_handler import LLMHandler

__all__ = ['GmailService', 'LLMHandler']