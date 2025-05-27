# src/core/workflow.py
import time
from typing import Any, TypedDict
from langgraph.graph import StateGraph, END
from src.utils.logger import logger
from src.agents.classification_agent import ClassifierAgent
from src.agents.demande_agent import DemandeAgent
from src.agents.field_extraction_agent import FieldExtractionAgent
from src.agents.subcategory_extraction_agent import SubcategoryExtractionAgent
from src.agents.priority_detection_agent import PriorityDetectionAgent
from src.agents.ticket_creation_agent import TicketCreationAgent
from src.agents.missing_fields_follow_up_agent import MissingFieldsFollowUpAgent
from src.agents.user_response_monitor import UserResponseMonitor
from src.agents.confirm_subcategory_follow_up_agent import ConfirmSubcategoryFollowUpAgent
from src.agents.subcategory_response_monitor import SubcategoryResponseMonitor
from src.agents.missing_subcategory_follow_up_agent import MissingSubcategoryFollowUpAgent
from src.agents.priority_follow_up_agent import PriorityFollowUpAgent
from src.agents.priority_response_monitor import PriorityResponseMonitor

# Constants
POLLING_INTERVAL = 30  # seconds

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
        user_responded: Boolean indicating if user has responded
        last_checked_at: Timestamp of last response check
        user: Dictionary containing user information
        subcategories: List of identified subcategories
        final_subcategory: String representing the selected/final subcategory
        priority: String indicating ticket priority level (CRITIQUE or ELEVEE)
        reason: String explaining the reason for priority determination
        description: String containing incident description
        affectation_team: String indicating which team should handle the ticket
    """
    email_data: dict
    processed: bool
    category: str
    status: str
    ticket_id: str
    missing_fields: list
    follow_up_sent_at: str
    user_responded: bool
    last_checked_at: str
    user: dict
    subcategories: list
    final_subcategory: str
    priority: str
    reason: str
    description: str
    affectation_team: str
    temp_priority_ticket_id: str

def create_workflow(
        classifier_agent: Any, 
        demande_agent: Any,
        field_extraction_agent: Any,
        subcategory_extraction_agent: Any,
        priority_detection_agent: Any,
        ticket_creation_agent: Any,
        missing_fields_follow_up_agent: Any,
        user_response_monitor: Any,
        confirm_subcategory_follow_up_agent: Any,
        subcategory_response_monitor: Any,
        missing_subcategory_follow_up_agent: Any,
        priority_follow_up_agent: Any,
        priority_response_monitor: Any
    ) -> Any:
    """
    Creates and configures the email processing workflow.
    
    Args:
        classifier_agent: Initialized ClassifierAgent instance
        demande_agent: Initialized DemandeAgent instance
        field_extraction_agent: Initialized FieldExtractionAgent instance
        subcategory_extraction_agent: Initialized SubcategoryExtractionAgent instance
        priority_detection_agent: Initialized PriorityDetectionAgent instance
        ticket_creation_agent: Initialized TicketCreationAgent instance
        missing_fields_follow_up_agent: Initialized MissingFieldsFollowUpAgent instance
        user_response_monitor: Initialized UserResponseMonitor instance
        confirm_subcategory_follow_up_agent: Initialized ConfirmSubcategoryFollowUpAgent instance
        subcategory_response_monitor: Initialized SubcategoryResponseMonitor instance
        missing_subcategory_follow_up_agent: Initialized MissingSubcategoryFollowUpAgent instance
        priority_follow_up_agent: Initialized PriorityFollowUpAgent instance
        priority_response_monitor: Initialized PriorityResponseMonitor instance
    Returns:
        Compiled LangGraph workflow ready for execution
    """
    logger.info("Initializing email processing workflow...")
    
    # Initialize the state graph
    workflow = StateGraph(EmailState)
    
    # Add nodes using passed agents
    workflow.add_node("classify_email", classifier_agent.classify_email)
    workflow.add_node("extract_user_info", field_extraction_agent.process)
    workflow.add_node("handle_demande", demande_agent.process)
    workflow.add_node("subcategory_extraction_agent", subcategory_extraction_agent.process)
    workflow.add_node("priority_detection_agent", priority_detection_agent.process)
    workflow.add_node("create_ticket", ticket_creation_agent.process)
    workflow.add_node("missing_fields_follow_up", missing_fields_follow_up_agent.process)
    workflow.add_node("check_fields_response", user_response_monitor.process)
    workflow.add_node("missing_subcategory_follow_up", missing_subcategory_follow_up_agent.process)
    workflow.add_node("confirm_subcategory_follow_up", confirm_subcategory_follow_up_agent.process)
    workflow.add_node("check_subcategory_response", subcategory_response_monitor.process)
    workflow.add_node("complete_processing", _mark_as_processed)
    workflow.add_node("priority_follow_up", priority_follow_up_agent.process)
    workflow.add_node("check_priority_response", priority_response_monitor.process)
    
    # Conditional routing from classification to user info extraction
    workflow.add_conditional_edges("classify_email", _route_based_on_category,
    {
        "demande": "handle_demande",
        "incident": "extract_user_info"
    }
    )
    workflow.add_conditional_edges("extract_user_info", _route_based_on_missing_fields,
        {
            "missing_fields": "missing_fields_follow_up",
            "no_missing_fields": "subcategory_extraction_agent"
        }
    )
    workflow.add_conditional_edges("check_fields_response", _route_based_on_user_response,
        {
            "waiting": "check_fields_response",
            "responded": "extract_user_info"
        }
    )
    workflow.add_conditional_edges("subcategory_extraction_agent", _route_based_on_subcategory,
        {
            "missing_subcategory_follow_up": "missing_subcategory_follow_up",
            "priority_detection": "priority_detection_agent",
            "confirm_subcategory_follow_up": "confirm_subcategory_follow_up"
        }
    )
    workflow.add_conditional_edges("check_subcategory_response", _route_based_on_subcategory_response,
        {
            "waiting": "check_subcategory_response",
            "responded": "subcategory_extraction_agent"
        }
    )
    workflow.add_conditional_edges("priority_detection_agent", _route_based_on_priority_detection,
        {
            "missing_priority": "priority_follow_up",
            "priority_detected": "create_ticket"
        }
    )
    workflow.add_conditional_edges("check_priority_response", _route_based_on_priority_response,
        {
            "waiting": "check_priority_response",
            "responded": "priority_detection_agent"
        }
    )
    # Add edges from handlers to completion
    workflow.add_edge("handle_demande", "complete_processing")
    workflow.add_edge("missing_fields_follow_up", "check_fields_response")
    workflow.add_edge("missing_subcategory_follow_up", "check_subcategory_response")
    workflow.add_edge("confirm_subcategory_follow_up", "check_subcategory_response")
    workflow.add_edge("priority_follow_up", "check_priority_response")
    workflow.add_edge("create_ticket", "complete_processing")

    # Final edge to end
    workflow.add_edge("complete_processing", END)
    
    # Set entry point
    workflow.set_entry_point("classify_email")
    
    # Compile the workflow
    compiled_workflow = workflow.compile()

    # Attach a process_message method
    def process_message(self, message_data):
        from langgraph.errors import GraphRecursionError
        try:
            return self.invoke(message_data, config={"recursion_limit": 1000000})
        except GraphRecursionError:
            logger.warning("GraphRecursionError hit: restarting workflow from the beginning.")
            # Retry once from the beginning
            return self.invoke(message_data, config={"recursion_limit": 1000000})
    import types
    compiled_workflow.process_message = types.MethodType(process_message, compiled_workflow)

    logger.info("Workflow compilation complete")
    return compiled_workflow

def _route_based_on_category(state: EmailState) -> str:
    """Route the email based on classification category."""
    category = state["category"].lower()
    logger.debug(f"Routing email to {category} handler")
    return category

def _route_based_on_missing_fields(state: EmailState) -> str:
    """
    Route the workflow based on whether required fields are missing.
    
    Args:
        state: Current workflow state containing user information
        
    Returns:
        str: Next node in the workflow ("missing_fields" or "no_missing_fields")
    """
    logger.debug("Checking for missing fields...")
    
    # Check if user field exists and has location
    user = state.get("user", {})
    if not user or not user.get("location"):
        # If we're already waiting for a response, keep waiting
        if state.get("status") == "waiting_for_location":
            logger.info("Still waiting for location response")
            return "missing_fields"
            
        logger.info("Location field is missing, routing to follow-up")
        return "missing_fields"
    
    logger.info("All required fields are present")
    return "no_missing_fields"

def _route_based_on_subcategory(state: EmailState) -> str:
    """
    Route the workflow based on subcategory analysis.
    
    Args:
        state: Current workflow state containing subcategories information
        
    Returns:        
        str: Next node in the workflow based on subcategory analysis
    """
    logger.debug("Analyzing subcategories for routing...")
    
    # Get subcategories from state
    subcategories = state.get("subcategories", [])
    
    # Case 1: No subcategories
    if not subcategories:
        logger.info("No subcategories found, routing to follow-up")
        return "missing_subcategory_follow_up"
    
    # Case 2: Single subcategory
    if len(subcategories) == 1:
        # Extract the subcategory value
        if isinstance(subcategories[0], dict):
            subcategory_value = subcategories[0].get("subcategory") or subcategories[0].get("category", "")
        else:
            subcategory_value = str(subcategories[0])
            
        # Set final_subcategory in the state
        state["final_subcategory"] = subcategory_value
        logger.info(f"Single subcategory found: {subcategory_value}, routing to priority detection")
        return "priority_detection"
    
    # Case 3: Multiple subcategories (2 or more)
    if len(subcategories) >= 2:
        # Sort subcategories by confidence in descending order, casting to float
        def safe_confidence(x):
            try:
                return float(x.get("confidence", 0))
            except (ValueError, TypeError):
                return 0.0
        sorted_subcats = sorted(subcategories, key=safe_confidence, reverse=True)
        top_confidence = safe_confidence(sorted_subcats[0])
        second_confidence = safe_confidence(sorted_subcats[1])
        confidence_diff = top_confidence - second_confidence
        logger.debug(f"Confidence difference between top subcategories: {confidence_diff}")
        
        if confidence_diff > 0.2:
            # Extract the top subcategory value
            if isinstance(sorted_subcats[0], dict):
                subcategory_value = sorted_subcats[0].get("subcategory") or sorted_subcats[0].get("category", "")
            else:
                subcategory_value = str(sorted_subcats[0])
                
            # Set final_subcategory in the state
            state["final_subcategory"] = subcategory_value
            logger.info(f"Selected subcategory with high confidence: {subcategory_value}")
            logger.info("Significant confidence difference detected, routing to priority detection")
            return "priority_detection"
        else:
            logger.info("Low confidence difference detected, routing to confirm subcategory")
            return "confirm_subcategory_follow_up"
    
    # Default case (should not reach here)
    logger.warning("Unexpected subcategory state, defaulting to follow-up")
    return "missing_subcategory_follow_up"

def _route_based_on_priority_detection(state: EmailState) -> str:
    """
    Route the workflow based on whether priority has been detected.
    
    Args:
        state: Current workflow state containing priority information
        
    Returns:
        str: Next node in the workflow ("missing_priority" or "priority_detected")
    """
    logger.debug("Checking priority detection result...")
    
    # Check if priority is set
    priority = state.get("priority", "")
    
    if not priority:
        logger.info("Priority not determined from email, routing to follow-up")
        return "missing_priority"
    
    logger.info(f"Priority detected as {priority}, proceeding with processing")
    return "priority_detected"

def _route_based_on_user_response(state: EmailState) -> str:
    """
    Route the workflow based on whether user has responded to fields clarification.
    
    Args:
        state: Current workflow state containing user response status
        
    Returns:
        str: Next node in the workflow ("waiting" or "responded")
    """
    logger.debug("Checking fields response status...")
    
    # Add delay between checks
    time.sleep(POLLING_INTERVAL)
    
    if state.get("user_responded", False):
        logger.info("User has responded to fields clarification, proceeding with processing")
        return "responded"
    
    logger.info("Waiting for fields response")
    return "waiting"

def _route_based_on_subcategory_response(state: EmailState) -> str:
    """
    Route the workflow based on whether user has responded to subcategory confirmation.
    
    Args:
        state: Current workflow state containing user response status
        
    Returns:
        str: Next node in the workflow ("waiting" or "responded")
    """
    logger.debug("Checking subcategory response status...")
    
    # Add delay between checks
    time.sleep(POLLING_INTERVAL)
    
    if state.get("user_responded", False):
        logger.info("User has responded to subcategory confirmation, proceeding with processing")
        return "responded"
    
    logger.info("Waiting for subcategory confirmation response")
    return "waiting"

def _route_based_on_priority_response(state: EmailState) -> str:
    """
    Route the workflow based on whether user has responded to the priority follow-up.
    Args:
        state: Current workflow state containing user response status
    Returns:
        str: Next node in the workflow ("waiting" or "responded")
    """
    logger.debug("Checking priority follow-up response status...")
    time.sleep(POLLING_INTERVAL)
    if state.get("user_responded", False):
        logger.info("User has responded to priority follow-up, proceeding with processing")
        return "responded"
    logger.info("Waiting for priority follow-up response")
    return "waiting"

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