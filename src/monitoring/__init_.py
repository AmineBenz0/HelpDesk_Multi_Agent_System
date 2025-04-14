# src/monitoring/__init__.py
"""
Monitoring components for the Helpdesk system.

Includes:
- GmailMonitor: Continuously checks and processes new emails
"""

from .gmail_monitor import GmailMonitor

__all__ = ['GmailMonitor']