# src/core/__init__.py
"""
Core components of the Helpdesk system.

Includes:
- GmailService: Handles Gmail API interactions
- LLMHandler: Manages LLM communications
- EmailProcessor: Processes and classifies emails
"""

from .gmail_service import GmailService
from .llm_handler import LLMHandler
from .email_processor import EmailProcessor

__all__ = ['GmailService', 'LLMHandler', 'EmailProcessor']