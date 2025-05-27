import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.ticket_management import TicketManager

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete ALL tickets? This cannot be undone! (yes/no): ")
    if confirm.lower() == "yes":
        manager = TicketManager()
        manager.delete_all_tickets()
        print("All tickets deleted from Elasticsearch.")
    else:
        print("Operation cancelled.") 