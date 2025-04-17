from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import json
import os
from pathlib import Path
from src.utils.logger import logger

class TicketType(Enum):
    INCIDENT = "Incident"
    SERVICE_REQUEST = "Service Request"
    OTHER = "Other"

class Priority(Enum):
    ELEVEE = "Élevée"
    CRITIQUE = "Critique"

class Status(Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

@dataclass
class User:
    name: str
    email: str
    location: str

@dataclass
class SupportAgent:
    name: str
    team: str

@dataclass
class Ticket:
    ticket_id: str
    submitted_by: User
    date_submitted: datetime
    ticket_type: TicketType
    description: str
    priority: Optional[Priority] = None
    assigned_to: Optional[SupportAgent] = None
    status: Status = Status.OPEN
    resolution_notes: Optional[str] = None
    date_resolved: Optional[datetime] = None
    subcategories: Optional[List[dict]] = None

    def to_dict(self) -> dict:
        """Convert ticket to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['date_submitted'] = self.date_submitted.isoformat()
        if self.date_resolved:
            data['date_resolved'] = self.date_resolved.isoformat()
        # Convert enums to their values
        data['ticket_type'] = self.ticket_type.value
        data['priority'] = self.priority.value if self.priority else None
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Ticket':
        """Create ticket from dictionary."""
        # Convert ISO format strings back to datetime
        data['date_submitted'] = datetime.fromisoformat(data['date_submitted'])
        if data.get('date_resolved'):
            data['date_resolved'] = datetime.fromisoformat(data['date_resolved'])
        
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