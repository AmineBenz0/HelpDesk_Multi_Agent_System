from typing import List, Dict, Optional
from datetime import datetime
import uuid
import json
import os
from pathlib import Path
from src.utils.logger import logger

class Ticket:
    def __init__(
        self,
        user: Dict,
        ticket_type: str,
        priority: str,
        description: str,
        subcategories: List[Dict],
        email_data: Dict = None,
        status: str = "open",
        ticket_id: Optional[str] = None,
        date_submitted: Optional[datetime] = None,
        date_resolved: Optional[datetime] = None,
        assigned_to: Optional[Dict] = None,
        resolution_notes: Optional[str] = None,
        notes: Optional[List[str]] = None,
        thread_id: Optional[str] = None,
        message_id: Optional[str] = None,
        is_temp: bool = False,
        stage: Optional[str] = None
    ):
        self.ticket_id = ticket_id or str(uuid.uuid4())
        self.user = user
        self.ticket_type = ticket_type
        self.priority = priority
        self.description = description
        self.subcategories = subcategories
        self.email_data = email_data or {}
        self.status = status
        self.date_submitted = date_submitted or datetime.now()
        self.date_resolved = date_resolved
        self.assigned_to = assigned_to
        self.resolution_notes = resolution_notes
        self.notes = notes or []
        self.thread_id = thread_id
        self.message_id = message_id
        self.is_temp = is_temp
        self.stage = stage

    def to_dict(self):
        return self.__dict__

    def save_to_file(self, base_dir="tickets"):
        date = self.date_submitted
        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
        
        # All tickets (temp and final) go in the same directory structure
        ticket_dir = Path(base_dir) / year / month / day
        ticket_dir.mkdir(parents=True, exist_ok=True)
        
        # Use thread_id as the filename base to ensure temp files overwrite each other
        # and final ticket overwrites the last temp file
        if self.thread_id:
            # Use a consistent filename for all temporary tickets, so they overwrite each other
            if self.is_temp:
                filename = f"{self.thread_id}_TEMP.json"
            else:
                filename = f"{self.thread_id}.json"
        else:
            # Fallback to ticket_id if thread_id is not available
            if self.is_temp:
                filename = f"{self.ticket_id}_TEMP.json"
            else:
                filename = f"{self.ticket_id}.json"
            
        ticket_path = ticket_dir / filename
        
        # Create a temporary file first
        temp_path = ticket_dir / f"{filename}.tmp"
        
        try:
            # Write to a temporary file first
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, default=str, ensure_ascii=False, indent=2)
                
            # Then replace the original file atomically
            # This ensures we don't end up with a partially written file if the operation is interrupted
            temp_path.replace(ticket_path)
            
            logger.debug(f"Successfully saved ticket to {ticket_path}")
            return ticket_path
            
        except Exception as e:
            logger.error(f"Error saving ticket to {ticket_path}: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            raise

class TicketManager:
    def __init__(self):
        self.tickets: Dict[str, Ticket] = {}
        self.counter_file = Path("tickets/counter.json")
        self.ticket_counter = self._load_counter()
    
    def _load_counter(self) -> int:
        """Load the ticket counter from file or initialize to 1"""
        if self.counter_file.exists():
            try:
                with open(self.counter_file, 'r') as f:
                    data = json.load(f)
                    return data.get('counter', 1)
            except Exception as e:
                print(f"Error loading counter: {str(e)}")
                return 1
        return 1
    
    def _save_counter(self) -> None:
        """Save the current ticket counter to file"""
        self.counter_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.counter_file, 'w') as f:
                json.dump({'counter': self.ticket_counter}, f)
        except Exception as e:
            print(f"Error saving counter: {str(e)}")
    
    def generate_ticket_id(self, date: datetime = None, is_temp: bool = False, stage: Optional[str] = None) -> str:
        """Generate a ticket ID in the format TKT-YYYYMMDD-XXXX or TEMP-STAGE-YYYYMMDD-XXXX"""
        if date is None:
            date = datetime.now()
        
        date_part = date.strftime("%Y%m%d")
        counter_part = f"{self.ticket_counter:04d}"
        
        if is_temp and stage:
            ticket_id = f"TEMP-{stage}-{date_part}-{counter_part}"
        else:
            ticket_id = f"TKT-{date_part}-{counter_part}"
        
        # Only increment counter for final tickets, not temporary ones
        if not is_temp:
            self.ticket_counter += 1
            self._save_counter()
        
        return ticket_id

    def create_ticket(self, **kwargs) -> Ticket:
        # Generate ticket ID if not provided
        is_temp = kwargs.get("is_temp", False)
        stage = kwargs.get("stage", None)
        
        if "ticket_id" not in kwargs:
            date = kwargs.get("date_submitted", datetime.now())
            kwargs["ticket_id"] = self.generate_ticket_id(date, is_temp, stage)
            
        ticket = Ticket(**kwargs)
        self.tickets[ticket.ticket_id] = ticket
        return ticket
    
    def create_temp_ticket(self, stage: str, **kwargs) -> Ticket:
        """Create a temporary ticket for a specific processing stage"""
        kwargs["is_temp"] = True
        kwargs["stage"] = stage
        # Set status to "in-progress" for all temporary tickets
        kwargs["status"] = "in-progress"
        return self.create_ticket(**kwargs)

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        return self.tickets.get(ticket_id)

    def get_all_tickets(self) -> Dict[str, Ticket]:
        return self.tickets 

    def finalize_temp_ticket(self, temp_ticket_id: str, **updates) -> Ticket:
        """Convert a temporary ticket to a final ticket.
        
        Args:
            temp_ticket_id: ID of the temporary ticket to finalize
            **updates: Any fields to update on the ticket
            
        Returns:
            The finalized ticket
        
        Raises:
            ValueError: If the ticket is not found or is not a temporary ticket
        """
        # Get the temporary ticket
        temp_ticket = self.tickets.get(temp_ticket_id)
        if not temp_ticket:
            raise ValueError(f"Temporary ticket {temp_ticket_id} not found")
        
        if not temp_ticket.is_temp:
            raise ValueError(f"Ticket {temp_ticket_id} is not a temporary ticket")
        
        # Create a copy of the ticket data
        ticket_data = temp_ticket.to_dict()
        
        # Make sure to preserve the thread_id for file overwriting
        thread_id = ticket_data.get('thread_id')
        if not thread_id:
            logger.warning(f"Temporary ticket {temp_ticket_id} missing thread_id")
        
        # Get the date for locating the temp file 
        date = ticket_data.get("date_submitted")
        if isinstance(date, str):
            # Convert string date back to datetime if needed
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except:
                date = datetime.now()
        else:
            date = date or datetime.now()
            
        # Get the path to the temporary file that needs to be deleted
        year = str(date.year)
        month = f"{date.month:02d}"
        day = f"{date.day:02d}"
        
        # Construct the path to the temp file
        base_dir = "tickets"
        if thread_id:
            temp_filename = f"{thread_id}_TEMP.json"
        else:
            temp_filename = f"{temp_ticket_id}_TEMP.json"
            
        temp_file_path = Path(base_dir) / year / month / day / temp_filename
        
        # Remove temporary-specific fields
        ticket_data.pop("is_temp")
        ticket_data.pop("stage")
        
        # Set status to open and apply any other updates
        ticket_data["status"] = "open"
        ticket_data.update(updates)
        
        # Generate a new ticket ID
        if "ticket_id" not in updates:
            ticket_data["ticket_id"] = self.generate_ticket_id(date)
        
        # Ensure thread_id is preserved if it was in the original ticket
        if thread_id and "thread_id" not in updates:
            ticket_data["thread_id"] = thread_id
        
        # Create the final ticket
        final_ticket = Ticket(**ticket_data)
        
        # Add it to the tickets dictionary
        self.tickets[final_ticket.ticket_id] = final_ticket
        
        # Save the final ticket
        final_ticket.save_to_file()
        
        # Delete the temporary file if it exists
        if temp_file_path.exists():
            try:
                logger.info(f"Deleting temporary ticket file: {temp_file_path}")
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary ticket file {temp_file_path}: {str(e)}")
        
        # Return the finalized ticket
        return final_ticket 