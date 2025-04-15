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
        classification_result: Dictionary containing LLM classification results
        processed: Boolean indicating whether processing is complete
        category: String representing the classified category
    """
    email_data: dict
    classification_result: dict
    processed: bool
    category: str

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
    
    # Define workflow edges
    workflow.add_edge(
        "classify_email", 
        "complete_processing",
    )
    
    workflow.add_edge(
        "complete_processing", 
        END,
    )

    # Conditional routing
    workflow.add_conditional_edges(
        "classify_email",
        _route_based_on_category,
        {
            "demande": "handle_demande",
            "incident": "handle_incident"
        }
    )
    
    # Set entry point
    workflow.set_entry_point("classify_email")
    
    # Compile the workflow
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow compilation complete")
    return compiled_workflow

def _route_based_on_category(state: EmailState) -> str:
    """Route the email based on classification category."""
    category = state["classification_result"].get("category", "").lower()
    print(category)
    print(state["classification_result"])
    logger.debug(f"Routing email to {category} handler")
    return "demande" if "demande" in category else "incident"

def _process_demande(state: EmailState) -> EmailState:
    result = DemandeAgent.process(state["email_data"])
    return {**state, "demande_result": result}

def _process_incident(state: EmailState) -> EmailState:
    result = IncidentAgent.process(state["email_data"])
    return {**state, "incident_result": result}

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