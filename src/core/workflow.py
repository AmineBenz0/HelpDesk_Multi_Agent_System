# src/core/workflow.py
from typing import Any, TypedDict
from langgraph.graph import StateGraph, END
from src.utils.logger import logger
from src.core.email_processor import EmailProcessor

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

def create_workflow(email_processor: EmailProcessor) -> Any:
    """
    Creates and configures the email processing workflow.
    
    Args:
        email_processor: Initialized EmailProcessor instance
        
    Returns:
        Compiled LangGraph workflow ready for execution
    """
    logger.info("Initializing email processing workflow...")
    
    # Initialize the state graph
    workflow = StateGraph(EmailState)
    
    # Add workflow nodes
    workflow.add_node(
        "classify_email", 
        email_processor.classify_email,
    )
    
    workflow.add_node(
        "complete_processing", 
        _mark_as_processed,
    )
    
    # Define workflow edges
    workflow.add_edge(
        "classify_email", 
        "complete_processing",
    )
    
    workflow.add_edge(
        "complete_processing", 
        END,
    )
    
    # Set entry point
    workflow.set_entry_point("classify_email")
    
    # Compile the workflow
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow compilation complete")
    return compiled_workflow

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