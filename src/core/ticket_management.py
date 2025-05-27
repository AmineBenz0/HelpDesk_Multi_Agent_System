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
    def __init__(self):
        self.tickets: Dict[str, Ticket] = {}
        self.ticket_counter = 1  # No file-based counter
        self.es_service = ElasticsearchService()
    
    def generate_ticket_id(self, date: datetime = None, is_temp: bool = False, stage: Optional[str] = None) -> str:
        if date is None:
            date = datetime.now()
        date_part = date.strftime("%Y%m%d")
        counter_part = f"{self.ticket_counter:04d}"
        if is_temp and stage:
            ticket_id = f"TEMP-{stage}-{date_part}-{counter_part}"
        else:
            ticket_id = f"TKT-{date_part}-{counter_part}"
        if not is_temp:
            self.ticket_counter += 1
        return ticket_id

    def create_ticket(self, **kwargs) -> Ticket:
        is_temp = kwargs.get("is_temp", False)
        stage = kwargs.get("stage", None)
        if "ticket_id" not in kwargs:
            date = kwargs.get("date_submitted", datetime.now())
            kwargs["ticket_id"] = self.generate_ticket_id(date, is_temp, stage)
        ticket = Ticket(**kwargs)
        self.tickets[ticket.ticket_id] = ticket
        ticket.save_to_elasticsearch()
        return ticket
    
    def create_temp_ticket(self, stage: str, **kwargs) -> Ticket:
        kwargs["is_temp"] = True
        kwargs["stage"] = stage
        kwargs["status"] = "in-progress"

        thread_id = kwargs.get("thread_id")
        if thread_id:
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
                for data in hits:
                    old_ticket_id = data.get("ticket_id")
                    if old_ticket_id:
                        self.es_service.delete_document(old_ticket_id)
                        if old_ticket_id in self.tickets:
                            del self.tickets[old_ticket_id]
                        logger.info(f"Deleted previous temp ticket {old_ticket_id} for thread {thread_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup previous temp tickets for thread {thread_id}: {e}")

        ticket = self.create_ticket(**kwargs)
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
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
        temp_ticket = self.get_ticket(temp_ticket_id)
        if not temp_ticket:
            raise ValueError(f"Temporary ticket {temp_ticket_id} not found")
        if not temp_ticket.is_temp:
            raise ValueError(f"Ticket {temp_ticket_id} is not a temporary ticket")

        ticket_data = temp_ticket.to_dict()
        thread_id = ticket_data.get("thread_id")
        ticket_data.pop("is_temp", None)
        ticket_data.pop("stage", None)
        ticket_data["status"] = "open"
        ticket_data.update(updates)
        # Ensure date_submitted is a datetime object
        date_submitted = ticket_data.get('date_submitted', datetime.now())
        if isinstance(date_submitted, str):
            try:
                date_submitted = datetime.fromisoformat(date_submitted)
            except Exception:
                date_submitted = datetime.now()
        if "ticket_id" not in updates:
            ticket_data["ticket_id"] = self.generate_ticket_id(date_submitted)
        final_ticket = Ticket(**ticket_data)
        self.tickets[final_ticket.ticket_id] = final_ticket
        final_ticket.save_to_elasticsearch()

        # Delete all temp tickets for this thread_id
        if thread_id:
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
                for data in hits:
                    old_ticket_id = data.get("ticket_id")
                    if old_ticket_id:
                        self.es_service.delete_document(old_ticket_id)
                        if old_ticket_id in self.tickets:
                            del self.tickets[old_ticket_id]
                        logger.info(f"Deleted temp ticket {old_ticket_id} for thread {thread_id} after finalization.")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp tickets for thread {thread_id} after finalization: {e}")

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