from elasticsearch import Elasticsearch

es = Elasticsearch(
    "http://localhost:9200",  # or your ES_HOST
)

ticket_index = "tickets"  # Adjust if your ticket index has a different name
counter_index = "ticket_counter"

# Find the latest ticket by date_submitted (assuming a 'date_submitted' field)
try:
    res = es.search(
        index=ticket_index,
        body={
            "size": 1,
            "sort": [{"date_submitted": {"order": "desc"}}],  # Changed from 'timestamp' to 'date_submitted'
            "query": {"match_all": {}}
        }
    )
    hits = res.get('hits', {}).get('hits', [])
    if not hits:
        print("No tickets found.")
    else:
        latest_ticket = hits[0]
        ticket_id = latest_ticket['_id']
        print(f"Deleting latest ticket with ID: {ticket_id}")
        es.delete(index=ticket_index, id=ticket_id)

        # Decrement the ticket counter by 1
        if es.indices.exists(index=counter_index):
            counter_doc = es.get(index=counter_index, id=counter_index, ignore=[404])
            if counter_doc.get('found'):
                current_count = counter_doc['_source'].get('count', 0)
                new_count = max(0, current_count - 1)
                es.index(index=counter_index, id=counter_index, body={"count": new_count})
                print(f"Ticket counter decremented to {new_count}.")
            else:
                print("Counter document not found.")
        else:
            print("Counter index does not exist.")
except Exception as e:
    print(f"Error deleting latest ticket: {e}") 