# src/main.py
import sys
import os

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import threading
import subprocess
import time
from typing import TypedDict
from langgraph.graph import StateGraph
from src.core.gmail_service import GmailService
from src.core.gmail_sender import GmailSender
from src.core.llm_handler import LLMHandler
from src.core.workflow import create_workflow
from src.monitoring.gmail_monitor import GmailMonitor
from src.utils.logger import logger
from src.agents.classification_agent import ClassifierAgent
from src.agents.demande_agent import DemandeAgent
from src.agents.incident_agent import IncidentAgent
from src.core.ticket_management import TicketManager

def run_dashboard():
    """Run the Streamlit dashboard in a separate process."""
    try:
        # Get the absolute path to the dashboard app
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')
        # Run Streamlit in a separate process
        subprocess.run(['streamlit', 'run', dashboard_path])
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")

def run_email_monitor(gmail_service, workflow):
    """Run the email monitoring system."""
    try:
        monitor = GmailMonitor(gmail_service.service, workflow)
        monitor.start_monitoring()
    except Exception as e:
        logger.error(f"Email monitor error: {str(e)}")

def main():
    """Main entry point for the Helpdesk system."""
    logger.info("Starting Helpdesk Email Processing System")
    
    try:
        # Initialize services
        gmail_service = GmailService()
        gmail_sender = GmailSender(gmail_service.service)
        llm_handler = LLMHandler()
        ticket_manager = TicketManager()

        # Initialize Agents
        classifier_agent = ClassifierAgent(llm_handler)
        demande_agent = DemandeAgent(gmail_sender)
        incident_agent = IncidentAgent(llm_handler, ticket_manager, gmail_sender)
        
        # Create workflow
        workflow = create_workflow(
            classifier_agent=classifier_agent,
            demande_agent=demande_agent,
            incident_agent=incident_agent
        )

        # Start email monitor in a separate thread
        email_thread = threading.Thread(
            target=run_email_monitor,
            args=(gmail_service, workflow),
            daemon=True
        )
        email_thread.start()

        # Start dashboard in a separate process
        dashboard_process = threading.Thread(
            target=run_dashboard,
            daemon=True
        )
        dashboard_process.start()

        # Keep the main process running
        while True:
            time.sleep(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()