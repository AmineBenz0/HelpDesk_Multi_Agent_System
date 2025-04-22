from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
import os
from pathlib import Path
from src.utils.logger import logger

class TicketType(Enum):
    DEMANDE = "Demande"
    INCIDENT = "Incident"
    SERVICE_REQUEST = "Service Request"

class Priority(Enum):
    ELEVEE = "Élevée"
    CRITIQUE = "Critique"

class Status(Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    ESCALATED = "Escalated"

@dataclass
class User:
    name: str
    email: str
    location: str

@dataclass
class SupportAgent:
    name: str
    email: str
    team: str

@dataclass
class Ticket:
    ticket_id: str
    submitted_by: User
    date_submitted: datetime
    ticket_type: TicketType
    priority: Priority
    status: Status = Status.OPEN
    description: str = ""
    subcategories: List[Dict[str, Any]] = field(default_factory=list)
    assigned_to: Optional[SupportAgent] = None
    date_resolved: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    follow_up_sent_at: Optional[datetime] = None
    last_reminder_sent_at: Optional[datetime] = None
    response_timeout: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert ticket to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['date_submitted'] = self.date_submitted.isoformat()
        if self.date_resolved:
            data['date_resolved'] = self.date_resolved.isoformat()
        if self.follow_up_sent_at:
            data['follow_up_sent_at'] = self.follow_up_sent_at.isoformat()
        if self.last_reminder_sent_at:
            data['last_reminder_sent_at'] = self.last_reminder_sent_at.isoformat()
        if self.response_timeout:
            data['response_timeout'] = self.response_timeout.isoformat()
        # Convert enums to their values
        data['ticket_type'] = self.ticket_type.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Ticket':
        """Create ticket from dictionary."""
        # Convert ISO format strings back to datetime
        data['date_submitted'] = datetime.fromisoformat(data['date_submitted'])
        if data.get('date_resolved'):
            data['date_resolved'] = datetime.fromisoformat(data['date_resolved'])
        if data.get('follow_up_sent_at'):
            data['follow_up_sent_at'] = datetime.fromisoformat(data['follow_up_sent_at'])
        if data.get('last_reminder_sent_at'):
            data['last_reminder_sent_at'] = datetime.fromisoformat(data['last_reminder_sent_at'])
        if data.get('response_timeout'):
            data['response_timeout'] = datetime.fromisoformat(data['response_timeout'])
        
        # Handle priority encoding
        if data.get('priority'):
            priority_value = data['priority']
            # Handle common encoding issues
            if isinstance(priority_value, str):
                priority_value = priority_value.replace('Ã‰', 'É').replace('Ã©', 'é')
                if priority_value == 'Élevée':
                    data['priority'] = Priority.ELEVEE
                elif priority_value == 'Critique':
                    data['priority'] = Priority.CRITIQUE
                else:
                    data['priority'] = None
            else:
                data['priority'] = None
        
        # Convert string values back to enums
        data['ticket_type'] = TicketType(data['ticket_type'])
        data['status'] = Status(data['status'])
        return cls(**data)

    def add_note(self, note: str) -> None:
        """Add a note to the ticket."""
        self.notes.append(f"{datetime.now().isoformat()}: {note}")
        if not self.resolution_notes:
            self.resolution_notes = note
        else:
            self.resolution_notes += f"\n{note}"

    def set_follow_up_sent(self) -> None:
        """Mark that a follow-up email was sent."""
        self.follow_up_sent_at = datetime.now()

    def set_reminder_sent(self) -> None:
        """Mark that a reminder email was sent."""
        self.last_reminder_sent_at = datetime.now()

    def set_response_timeout(self, timeout_hours: int = 24) -> None:
        """Set the response timeout for the ticket."""
        self.response_timeout = datetime.now() + timedelta(hours=timeout_hours)

    def has_timed_out(self) -> bool:
        """Check if the ticket has timed out waiting for response."""
        if not self.response_timeout:
            return False
        return datetime.now() > self.response_timeout

    def needs_reminder(self, reminder_interval_hours: int = 6) -> bool:
        """Check if the ticket needs a reminder."""
        if not self.follow_up_sent_at:
            return False
        if self.last_reminder_sent_at:
            time_since_last_reminder = datetime.now() - self.last_reminder_sent_at
            return time_since_last_reminder.total_seconds() >= reminder_interval_hours * 3600
        time_since_follow_up = datetime.now() - self.follow_up_sent_at
        return time_since_follow_up.total_seconds() >= reminder_interval_hours * 3600

class TicketManager:
    def __init__(self, base_dir: str = "tickets"):
        self.base_dir = Path(base_dir)
        self.tickets = {}
        self.ticket_counter = 0
        self._ensure_directory_structure()
        self._load_existing_tickets()

    def _ensure_directory_structure(self):
        """Ensure the ticket directory structure exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ticket storage directory: {self.base_dir.absolute()}")

    def _get_ticket_path(self, ticket_id: str) -> Path:
        """Get the path where a ticket should be stored."""
        # Extract date from ticket ID (TCK-YYYYMMDD-XXXX)
        date_str = ticket_id.split('-')[1]
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        
        # Create year/month/day directory structure
        ticket_dir = self.base_dir / year / month / day
        ticket_dir.mkdir(parents=True, exist_ok=True)
        
        return ticket_dir / f"{ticket_id}.json"

    def _load_existing_tickets(self):
        """Load existing tickets from the storage directory."""
        logger.info("Loading existing tickets...")
        for year_dir in self.base_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir():
                        continue
                    for ticket_file in day_dir.glob("*.json"):
                        try:
                            # Check if file is empty
                            if ticket_file.stat().st_size == 0:
                                logger.warning(f"Empty ticket file found: {ticket_file}")
                                continue
                                
                            with open(ticket_file, 'r', encoding='utf-8') as f:
                                ticket_data = json.load(f)
                                if not ticket_data:  # Check if JSON is empty
                                    logger.warning(f"Empty JSON in ticket file: {ticket_file}")
                                    continue
                                    
                                # Convert submitted_by dictionary back to User object
                                if 'submitted_by' in ticket_data:
                                    user_data = ticket_data['submitted_by']
                                    ticket_data['submitted_by'] = User(
                                        name=user_data['name'],
                                        email=user_data['email'],
                                        location=user_data['location']
                                    )
                                    
                                ticket = Ticket.from_dict(ticket_data)
                                self.tickets[ticket.ticket_id] = ticket
                                # Update counter to avoid ID conflicts
                                counter = int(ticket.ticket_id.split('-')[-1])
                                self.ticket_counter = max(self.ticket_counter, counter)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in ticket file {ticket_file}: {str(e)}")
                            # Create backup of corrupted file
                            backup_path = ticket_file.with_suffix('.json.bak')
                            ticket_file.rename(backup_path)
                            logger.info(f"Created backup of corrupted file: {backup_path}")
                        except Exception as e:
                            logger.error(f"Failed to load ticket {ticket_file}: {str(e)}")
        logger.info(f"Loaded {len(self.tickets)} existing tickets")

    def _save_ticket(self, ticket: Ticket):
        """Save a ticket to the filesystem."""
        ticket_path = self._get_ticket_path(ticket.ticket_id)
        try:
            with open(ticket_path, 'w', encoding='utf-8') as f:
                json.dump(ticket.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved ticket {ticket.ticket_id} to {ticket_path}")
        except Exception as e:
            logger.error(f"Failed to save ticket {ticket.ticket_id}: {str(e)}")
            raise

    def generate_ticket_id(self) -> str:
        """Generate a unique ticket ID in the format TCK-YYYYMMDD-XXXX."""
        self.ticket_counter += 1
        date_str = datetime.now().strftime("%Y%m%d")
        return f"TCK-{date_str}-{self.ticket_counter:04d}"

    def create_ticket(
        self,
        user: User,
        ticket_type: TicketType,
        priority: Optional[Priority] = None,
        description: str = "",
        subcategories: Optional[List[dict]] = None
    ) -> Ticket:
        """Create a new ticket."""
        ticket_id = self.generate_ticket_id()
        
        # Set default priority if none provided
        if priority is None:
            priority = Priority.ELEVEE  # Default to high priority
            
        ticket = Ticket(
            ticket_id=ticket_id,
            submitted_by=user,
            date_submitted=datetime.now(),
            ticket_type=ticket_type,
            priority=priority,
            description=description,
            subcategories=subcategories
        )
        self.tickets[ticket_id] = ticket
        self._save_ticket(ticket)
        return ticket

    def assign_ticket(self, ticket_id: str, agent: SupportAgent) -> bool:
        """Assign a ticket to a support agent."""
        if ticket_id not in self.tickets:
            return False
        self.tickets[ticket_id].assigned_to = agent
        self.tickets[ticket_id].status = Status.IN_PROGRESS
        self._save_ticket(self.tickets[ticket_id])
        return True

    def update_status(self, ticket_id: str, status: Status) -> bool:
        """Update the status of a ticket."""
        if ticket_id not in self.tickets:
            return False
        self.tickets[ticket_id].status = status
        if status == Status.RESOLVED or status == Status.CLOSED:
            self.tickets[ticket_id].date_resolved = datetime.now()
        self._save_ticket(self.tickets[ticket_id])
        return True

    def add_resolution_notes(self, ticket_id: str, notes: str) -> bool:
        """Add resolution notes to a ticket."""
        if ticket_id not in self.tickets:
            return False
        self.tickets[ticket_id].resolution_notes = notes
        self._save_ticket(self.tickets[ticket_id])
        return True

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Retrieve a ticket by its ID."""
        return self.tickets.get(ticket_id)

    def get_tickets_by_status(self, status: Status) -> List[Ticket]:
        """Get all tickets with a specific status."""
        return [ticket for ticket in self.tickets.values() if ticket.status == status]

    def get_tickets_by_agent(self, agent: SupportAgent) -> List[Ticket]:
        """Get all tickets assigned to a specific agent."""
        return [ticket for ticket in self.tickets.values() 
                if ticket.assigned_to and 
                ticket.assigned_to.name == agent.name and 
                ticket.assigned_to.team == agent.team]

    def get_tickets_by_priority(self, priority: Priority) -> List[Ticket]:
        """Get all tickets with a specific priority."""
        return [ticket for ticket in self.tickets.values() if ticket.priority == priority]

    def get_tickets_by_type(self, ticket_type: TicketType) -> List[Ticket]:
        """Get all tickets of a specific type."""
        return [ticket for ticket in self.tickets.values() if ticket.ticket_type == ticket_type]

    def get_tickets_by_subcategory(self, subcategory: str) -> List[Ticket]:
        """Get all tickets with a specific subcategory."""
        return [ticket for ticket in self.tickets.values() 
                if ticket.subcategories and 
                any(sc["category"] == subcategory for sc in ticket.subcategories)]

    def update_ticket_subcategories(self, ticket_id: str, subcategories: List[dict]) -> bool:
        """Update the subcategories of a ticket.
        
        Args:
            ticket_id: The ID of the ticket to update
            subcategories: New list of subcategories
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if ticket_id not in self.tickets:
            logger.error(f"Ticket {ticket_id} not found")
            return False
            
        try:
            self.tickets[ticket_id].subcategories = subcategories
            self._save_ticket(self.tickets[ticket_id])
            logger.info(f"Updated subcategories for ticket {ticket_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update subcategories for ticket {ticket_id}: {str(e)}")
            return False

    def get_all_tickets(self) -> Dict[str, Ticket]:
        """Get all tickets from the manager.
        
        Returns:
            Dict[str, Ticket]: Dictionary of all tickets with ticket IDs as keys
        """
        return self.tickets