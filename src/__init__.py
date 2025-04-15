# src/__init__.py
"""
Core functionality for the Helpdesk Multi-Agent System.

Exposes main components for easy import:
from src import GmailService, LLMHandler
"""

from .core.gmail_service import GmailService
from .core.llm_handler import LLMHandler
from .monitoring.gmail_monitor import GmailMonitor

__all__ = ['GmailService', 'LLMHandler', 'GmailMonitor']