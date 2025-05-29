from elasticsearch import Elasticsearch

es = Elasticsearch(
    "http://localhost:9200",  # or your ES_HOST
)

# Get all indices except system indices (those starting with '.')
indices = [idx for idx in es.indices.get_alias(index="*") if not idx.startswith(".")]

for idx in indices:
    print(f"Deleting index: {idx}")
    es.indices.delete(index=idx)

# Also delete the ticket counter and thread counter indices
for special_index in ["ticket_counter", "ticket_thread_counter"]:
    try:
        if es.indices.exists(index=special_index):
            print(f"Deleting special index: {special_index}")
            es.indices.delete(index=special_index)
    except Exception as e:
        print(f"Error deleting {special_index}: {e}")

print("All user indices and counters deleted.")