# src/main.py
import sys
import os
import time
import threading
from pathlib import Path

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
from src.core.ticket_management import TicketManager
from src.core.workflow import create_workflow
from src.monitoring.gmail_monitor import GmailMonitor
from src.utils.logger import logger
from src.agents.classification_agent import ClassifierAgent
from src.agents.demande_agent import DemandeAgent
from src.agents.field_extraction_agent import FieldExtractionAgent
from src.agents.missing_fields_follow_up_agent import MissingFieldsFollowUpAgent
from src.agents.user_response_monitor import UserResponseMonitor
from src.agents.subcategory_extraction_agent import SubcategoryExtractionAgent
from src.agents.priority_detection_agent import PriorityDetectionAgent
from src.agents.ticket_creation_agent import TicketCreationAgent
from src.agents.confirm_subcategory_follow_up_agent import ConfirmSubcategoryFollowUpAgent
from src.agents.subcategory_response_monitor import SubcategoryResponseMonitor
from src.agents.missing_subcategory_follow_up_agent import MissingSubcategoryFollowUpAgent
from src.agents.priority_follow_up_agent import PriorityFollowUpAgent
from src.agents.priority_response_monitor import PriorityResponseMonitor

def run_dashboard():
    """Run the dashboard in a subprocess."""
    try:
        # Get the absolute path to the dashboard app
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')
        # Run Streamlit in a separate process
        subprocess.run(['streamlit', 'run', dashboard_path])
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")

def run_email_monitor(gmail_service, workflow):
    """Run the email monitor in a thread."""
    try:
        # Use the base GmailMonitor
        monitor = GmailMonitor(gmail_service.service, workflow)
        logger.info("Starting Gmail Monitor...")
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
        field_extraction_agent = FieldExtractionAgent(llm_handler, gmail_service, ticket_manager)
        missing_fields_follow_up_agent = MissingFieldsFollowUpAgent(gmail_sender, llm_handler)
        user_response_monitor = UserResponseMonitor(gmail_service.service, llm_handler)
        subcategory_extraction_agent = SubcategoryExtractionAgent(llm_handler, ticket_manager)    
        priority_detection_agent = PriorityDetectionAgent(llm_handler, ticket_manager)
        ticket_creation_agent = TicketCreationAgent(ticket_manager)
        confirm_subcategory_follow_up_agent = ConfirmSubcategoryFollowUpAgent(gmail_sender, llm_handler)
        subcategory_response_monitor = SubcategoryResponseMonitor(gmail_service.service, llm_handler)
        missing_subcategory_follow_up_agent = MissingSubcategoryFollowUpAgent(gmail_sender, llm_handler)
        priority_follow_up_agent = PriorityFollowUpAgent(gmail_sender, llm_handler)
        priority_response_monitor = PriorityResponseMonitor(gmail_service.service, llm_handler)
        
        # Create workflow
        workflow = create_workflow(
            classifier_agent=classifier_agent,
            demande_agent=demande_agent,
            field_extraction_agent=field_extraction_agent,
            subcategory_extraction_agent=subcategory_extraction_agent,
            priority_detection_agent=priority_detection_agent,
            ticket_creation_agent=ticket_creation_agent,
            missing_fields_follow_up_agent=missing_fields_follow_up_agent,
            user_response_monitor=user_response_monitor,
            confirm_subcategory_follow_up_agent=confirm_subcategory_follow_up_agent,
            subcategory_response_monitor=subcategory_response_monitor,
            missing_subcategory_follow_up_agent=missing_subcategory_follow_up_agent,
            priority_follow_up_agent=priority_follow_up_agent,
            priority_response_monitor=priority_response_monitor
        )

        # Start email monitor in a separate thread
        email_thread = threading.Thread(
            target=run_email_monitor,
            args=(gmail_service, workflow),
            daemon=True
        )
        email_thread.start()

        #Start dashboard in a separate process
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