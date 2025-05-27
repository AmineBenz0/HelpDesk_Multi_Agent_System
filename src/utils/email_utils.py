from typing import Dict, Any, Optional
from src.utils.logger import logger

def ensure_thread_persistence(email_data: Dict[str, Any], messages: Optional[list] = None) -> Dict[str, Any]:
    """
    Ensure thread persistence when updating email_data by preserving the persistent_thread_id.
    
    Args:
        email_data: The original email_data dictionary
        messages: Optional new messages to update in the email_data
        
    Returns:
        Updated email_data with persistent_thread_id preserved
    """
    # Create a copy of the original email_data
    updated_email_data = dict(email_data)
    
    # Update messages if provided
    if messages is not None:
        updated_email_data["messages"] = messages
    
    # Ensure persistent_thread_id is preserved
    if "persistent_thread_id" in email_data:
        thread_id = email_data["persistent_thread_id"]
        updated_email_data["persistent_thread_id"] = thread_id
        logger.debug(f"Thread persistence maintained: persistent_thread_id={thread_id}")
    else:
        logger.warning("No persistent_thread_id found in email_data")
    
    return updated_email_data