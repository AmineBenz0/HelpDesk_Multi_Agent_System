# src/core/workflow.py
from typing import Any, TypedDict
from langgraph.graph import StateGraph, END
from src.utils.logger import logger
from src.agents.classification_agent import ClassifierAgent
from src.agents.demande_agent import DemandeAgent
from src.agents.incident_agent import IncidentAgent

class EmailState(TypedDict):
    """
    State definition for the email processing workflow.
    
    Attributes:
        email_data: Dictionary containing email metadata and content
        processed: Boolean indicating whether processing is complete
        category: String representing the classified category
        status: String representing the current processing status
        ticket_id: String representing the ticket ID if created
        missing_fields: List of missing fields if follow-up needed
        follow_up_sent_at: Timestamp when follow-up was sent
    """
    email_data: dict
    processed: bool
    category: str
    status: str
    ticket_id: str
    missing_fields: list
    follow_up_sent_at: str

def create_workflow(
        classifier_agent: Any, 
        demande_agent: Any,
        incident_agent: Any
    ) -> Any:
    """
    Creates and configures the email processing workflow.
    
    Args:
        email_processor: Initialized ClassifierAgent instance
        
    Returns:
        Compiled LangGraph workflow ready for execution
    """
    logger.info("Initializing email processing workflow...")
    
    # Initialize the state graph
    workflow = StateGraph(EmailState)
    
    # Add nodes using passed agents
    workflow.add_node("classify_email", classifier_agent.classify_email)
    workflow.add_node("handle_demande", demande_agent.process)
    workflow.add_node("handle_incident", incident_agent.process)
    workflow.add_node("complete_processing", _mark_as_processed)
    
    # Conditional routing from classification to handlers
    workflow.add_conditional_edges(
        "classify_email",
        _route_based_on_category,
        {
            "demande": "handle_demande",
            "incident": "handle_incident"
        }
    )
    
    # Add edges from handlers to completion
    workflow.add_edge("handle_demande", "complete_processing")
    
    # For incidents, check if follow-up is needed
    workflow.add_conditional_edges(
        "handle_incident",
        _check_incident_status,
        {
            "incident_escalated": "complete_processing",
            "incident_escalated_with_follow_up": "complete_processing"
        }
    )
    
    # Final edge to end
    workflow.add_edge("complete_processing", END)
    
    # Set entry point
    workflow.set_entry_point("classify_email")
    
    # Compile the workflow
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow compilation complete")
    return compiled_workflow

def _route_based_on_category(state: EmailState) -> str:
    """Route the email based on classification category."""
    category = state["category"].lower()
    logger.debug(f"Routing email to {category} handler")
    return category

def _check_incident_status(state: EmailState) -> str:
    """Check the status of incident processing."""
    status = state.get("status", "")
    logger.debug(f"Checking incident status: {status}")
    return status

def _mark_as_processed(state: EmailState) -> EmailState:
    """
    Internal function to mark email processing as complete.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with processed flag set to True
    """
    logger.debug("Marking email processing as complete")
    return {**state, "processed": True}