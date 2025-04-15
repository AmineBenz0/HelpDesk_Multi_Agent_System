# src/main.py
import sys
import os

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from typing import TypedDict
from langgraph.graph import StateGraph
from src.core.gmail_service import GmailService
from src.core.llm_handler import LLMHandler
from src.core.workflow import create_workflow
from src.monitoring.gmail_monitor import GmailMonitor
from src.utils.logger import logger
from src.agents.classification_agent import ClassifierAgent
from src.agents.demande_agent import DemandeAgent
from src.agents.incident_agent import IncidentAgent

def main():
    """Main entry point for the email notification system."""
    logger.info("Starting Helpdesk Email Processing System")
    
    try:
        # Initialize services
        gmail_service = GmailService().service
        llm_handler = LLMHandler()

        #Initialize Agents
        classifier_agent = ClassifierAgent(llm_handler)
        demande_agent = DemandeAgent(gmail_service)
        incident_agent = IncidentAgent()
        
        # Create and run workflow
        workflow = create_workflow(
            classifier_agent=classifier_agent,
            demande_agent=demande_agent,
            incident_agent=incident_agent
            )
        monitor = GmailMonitor(gmail_service, workflow)
        monitor.start_monitoring()
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()