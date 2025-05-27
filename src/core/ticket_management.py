from typing import List, Dict, Optional
from datetime import datetime
import uuid
from src.utils.logger import logger
from src.core.elasticsearch_service import ElasticsearchService

class Ticket:
    def __init__(
        self,
        user: Dict,
        ticket_type: str,
        priority: str,
        description: str,
        subcategories: List[Dict],
        final_subcategory: str = "",
        affectation_team: str = "",
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
        self.final_subcategory = final_subcategory
        self.affectation_team = affectation_team
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
        d = self.__dict__.copy()
        # Convert datetime fields for ES
        if isinstance(d.get('date_submitted'), datetime):
            d['date_submitted'] = d['date_submitted'].isoformat()
        if isinstance(d.get('date_resolved'), datetime):
            d['date_resolved'] = d['date_resolved'].isoformat() if d['date_resolved'] else None
        return d

    def save_to_elasticsearch(self):
        es_service = ElasticsearchService()
        doc = self.to_dict()
        es_service.index_document(doc, doc_id=self.ticket_id)
        logger.debug(f"Saved ticket {self.ticket_id} to Elasticsearch")
        return self.ticket_id

class TicketManager:
    # Index name for the ticket counter in Elasticsearch
    COUNTER_INDEX = "ticket_counter"
    COUNTER_DOC_ID = "ticket_counter"
    THREAD_COUNTER_INDEX = "ticket_thread_counter"  # New index for thread_id to counter mapping
    
    def __init__(self):
        self.tickets: Dict[str, Ticket] = {}
        self.es_service = ElasticsearchService()
        self._initialize_counter()
    
    def _initialize_counter(self):
        """Initialize the ticket counter from Elasticsearch or create it if it doesn't exist."""
        try:
            # Ensure counter index exists
            self.es_service.create_index_if_not_exists(index=self.COUNTER_INDEX)
            
            # Get counter document
            counter_doc = self.es_service.get_document(self.COUNTER_DOC_ID, index=self.COUNTER_INDEX)
            if counter_doc:
                self.ticket_counter = counter_doc.get("value", 1)
                logger.debug(f"Initialized ticket counter from Elasticsearch: {self.ticket_counter}")
            else:
                self.ticket_counter = 1
                self._save_counter()
                logger.debug("Created new ticket counter in Elasticsearch")
        except Exception as e:
            logger.warning(f"Could not initialize ticket counter from Elasticsearch: {e}")
            self.ticket_counter = 1
    
    def _save_counter(self):
        """Save the current ticket counter to Elasticsearch."""
        try:
            self.es_service.index_document(
                {"value": self.ticket_counter}, 
                doc_id=self.COUNTER_DOC_ID, 
                index=self.COUNTER_INDEX
            )
            logger.debug(f"Saved ticket counter to Elasticsearch: {self.ticket_counter}")
        except Exception as e:
            logger.error(f"Failed to save ticket counter to Elasticsearch: {e}")
    
    def _increment_counter(self):
        """Increment the ticket counter and save it to Elasticsearch."""
        try:
            # Use current counter value
            current_value = self.ticket_counter
            
            # Increment for next use
            self.ticket_counter += 1
            self._save_counter()
            
            return current_value
        except Exception as e:
            logger.error(f"Error incrementing ticket counter: {e}")
            # In case of error, still increment the in-memory counter but don't rely on persistence
            return self.ticket_counter
    
    def _get_or_create_thread_counter(self, thread_id: Optional[str]) -> int:
        """
        Get the counter value for a thread_id, or create it if it doesn't exist.
        """
        if not thread_id:
            return None
        # Try to get the mapping from ES
        try:
            doc = self.es_service.get_document(thread_id, index=self.THREAD_COUNTER_INDEX)
            if doc and "counter" in doc:
                return doc["counter"]
            else:
                # Assign new counter value
                counter_value = self._increment_counter()
                self.es_service.create_index_if_not_exists(index=self.THREAD_COUNTER_INDEX)
                self.es_service.index_document({"counter": counter_value}, doc_id=thread_id, index=self.THREAD_COUNTER_INDEX)
                return counter_value
        except Exception as e:
            logger.warning(f"Could not get or create thread counter for {thread_id}: {e}")
            # Fallback: just increment global counter (may cause duplicates if ES is down)
            return self._increment_counter()

    def generate_ticket_id(self, date: datetime = None, is_temp: bool = False, stage: Optional[str] = None, thread_id: Optional[str] = None) -> str:
        """
        Generate a unique ticket ID.
        If thread_id is provided, use the same counter for all tickets (temp/final) in that thread.
        """
        if date is None:
            date = datetime.now()
        date_part = date.strftime("%Y%m%d")
        if thread_id:
            counter_value = self._get_or_create_thread_counter(thread_id)
        else:
            counter_value = self._increment_counter()
        counter_part = f"{counter_value:05d}"
        # Generate thread part if thread_id is provided
        thread_part = ""
        if thread_id:
            thread_hash = str(abs(hash(thread_id)))[:8]
            thread_part = f"-{thread_hash}"
        if is_temp and stage:
            ticket_id = f"TEMP-{stage}-{date_part}{thread_part}-{counter_part}"
        else:
            ticket_id = f"TKT-{date_part}{thread_part}-{counter_part}"
        return ticket_id

    def create_ticket(self, **kwargs) -> Ticket:
        """Create a new ticket and save it to Elasticsearch."""
        is_temp = kwargs.get("is_temp", False)
        stage = kwargs.get("stage", None)
        thread_id = kwargs.get("thread_id", None)
        
        if "ticket_id" not in kwargs:
            date = kwargs.get("date_submitted", datetime.now())
            kwargs["ticket_id"] = self.generate_ticket_id(date, is_temp, stage, thread_id)
        
        ticket = Ticket(**kwargs)
        self.tickets[ticket.ticket_id] = ticket
        ticket.save_to_elasticsearch()
        return ticket
    
    def create_temp_ticket(self, stage: str, **kwargs) -> Ticket:
        """
        Create a temporary ticket for a specific stage.
        Deletes any existing temporary tickets for the same thread if provided.
        """
        kwargs["is_temp"] = True
        kwargs["stage"] = stage
        kwargs["status"] = "in-progress"

        thread_id = kwargs.get("thread_id")
        if thread_id:
            # Delete any existing temporary tickets for this thread
            self._delete_temp_tickets_for_thread(thread_id)
        
        ticket = self.create_ticket(**kwargs)
        return ticket
    
    def _delete_temp_tickets_for_thread(self, thread_id: str) -> int:
        """
        Delete all temporary tickets for a given thread ID.
        
        Args:
            thread_id: The thread ID to delete temporary tickets for
            
        Returns:
            The number of tickets deleted
        """
        if not thread_id:
            return 0
            
        query = {
            "bool": {
                "must": [
                    {"term": {"is_temp": True}},
                    {"term": {"thread_id": thread_id}}
                ]
            }
        }
        
        try:
            hits = self.es_service.search_documents(query)
            deleted_count = 0
            
            for data in hits:
                old_ticket_id = data.get("ticket_id")
                if old_ticket_id:
                    self.es_service.delete_document(old_ticket_id)
                    if old_ticket_id in self.tickets:
                        del self.tickets[old_ticket_id]
                    deleted_count += 1
                    
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} previous temp tickets for thread {thread_id}")
            
            return deleted_count
        except Exception as e:
            logger.warning(f"Failed to cleanup previous temp tickets for thread {thread_id}: {e}")
            return 0

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get a ticket by its ID from Elasticsearch."""
        try:
            data = self.es_service.get_document(ticket_id)
            if not data:
                return None
            # Convert date fields back to datetime
            if 'date_submitted' in data:
                data['date_submitted'] = datetime.fromisoformat(data['date_submitted'])
            if 'date_resolved' in data and data['date_resolved']:
                data['date_resolved'] = datetime.fromisoformat(data['date_resolved'])
            return Ticket(**data)
        except Exception as e:
            logger.error(f"Error fetching ticket {ticket_id} from Elasticsearch: {e}")
            return None

    def get_all_tickets(self) -> Dict[str, Ticket]:
        """Get all tickets from Elasticsearch."""
        tickets = {}
        try:
            hits = self.es_service.search_documents({"match_all": {}})
            for data in hits:
                if 'date_submitted' in data:
                    data['date_submitted'] = datetime.fromisoformat(data['date_submitted'])
                if 'date_resolved' in data and data['date_resolved']:
                    data['date_resolved'] = datetime.fromisoformat(data['date_resolved'])
                ticket = Ticket(**data)
                tickets[ticket.ticket_id] = ticket
        except Exception as e:
            # If the error is NotFoundError and it's about the index, just log info and return empty
            if hasattr(e, 'status_code') and e.status_code == 404 and 'index_not_found_exception' in str(e):
                logger.info("No tickets index found in Elasticsearch. Returning empty ticket list.")
            else:
                logger.error(f"Error fetching all tickets from Elasticsearch: {e}")
        return tickets

    def finalize_temp_ticket(self, temp_ticket_id: str, **updates) -> Ticket:
        """
        Finalize a temporary ticket by converting it to a permanent ticket.
        
        Args:
            temp_ticket_id: The ID of the temporary ticket to finalize
            **updates: Additional updates to apply to the ticket
            
        Returns:
            The finalized ticket
        """
        temp_ticket = self.get_ticket(temp_ticket_id)
        if not temp_ticket:
            raise ValueError(f"Temporary ticket {temp_ticket_id} not found")
        if not temp_ticket.is_temp:
            raise ValueError(f"Ticket {temp_ticket_id} is not a temporary ticket")

        # Extract ticket data and thread ID
        ticket_data = temp_ticket.to_dict()
        thread_id = ticket_data.get("thread_id")
        
        # Remove temporary flags
        ticket_data.pop("is_temp", None)
        ticket_data.pop("stage", None)
        ticket_data["status"] = "open"
        
        # Apply updates
        ticket_data.update(updates)
        
        # Ensure date_submitted is a datetime object
        date_submitted = ticket_data.get('date_submitted', datetime.now())
        if isinstance(date_submitted, str):
            try:
                date_submitted = datetime.fromisoformat(date_submitted)
            except Exception:
                date_submitted = datetime.now()
        
        # Generate new ticket ID if not provided
        if "ticket_id" not in updates:
            ticket_data["ticket_id"] = self.generate_ticket_id(date_submitted, thread_id=thread_id)
        
        # Create final ticket
        final_ticket = Ticket(**ticket_data)
        self.tickets[final_ticket.ticket_id] = final_ticket
        final_ticket.save_to_elasticsearch()
        
        # Delete the temporary ticket
        self.delete_ticket(temp_ticket_id)
        
        # Delete all other temp tickets for this thread_id
        if thread_id:
            self._delete_temp_tickets_for_thread(thread_id)
            
        return final_ticket

    def delete_ticket(self, ticket_id: str) -> bool:
        """
        Delete a ticket by its ID from Elasticsearch and remove from memory.
        Returns True if deleted, False otherwise.
        """
        try:
            result = self.es_service.delete_document(ticket_id)
            if ticket_id in self.tickets:
                del self.tickets[ticket_id]
            logger.info(f"Deleted ticket {ticket_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete ticket {ticket_id}: {e}")
            return False 

    def delete_all_tickets(self):
        """
        Delete all tickets from Elasticsearch and clear in-memory tickets.
        """
        self.es_service.delete_all_documents()
        self.tickets.clear()
        logger.info("All tickets deleted from Elasticsearch and memory.") 
        
    def get_tickets_by_thread_id(self, thread_id: str, include_temp: bool = False) -> List[Ticket]:
        """
        Get all tickets for a specific thread ID.
        
        Args:
            thread_id: The thread ID to get tickets for
            include_temp: Whether to include temporary tickets
            
        Returns:
            A list of tickets
        """
        if not thread_id:
            return []
            
        query = {
            "bool": {
                "must": [
                    {"term": {"thread_id": thread_id}}
                ]
            }
        }
        
        if not include_temp:
            query["bool"]["must_not"] = [{"term": {"is_temp": True}}]
        
        try:
            hits = self.es_service.search_documents(query)
            tickets = []
            
            for data in hits:
                if 'date_submitted' in data:
                    data['date_submitted'] = datetime.fromisoformat(data['date_submitted'])
                if 'date_resolved' in data and data['date_resolved']:
                    data['date_resolved'] = datetime.fromisoformat(data['date_resolved'])
                ticket = Ticket(**data)
                tickets.append(ticket)
                
            return tickets
        except Exception as e:
            logger.error(f"Error fetching tickets for thread {thread_id} from Elasticsearch: {e}")
            return [] 