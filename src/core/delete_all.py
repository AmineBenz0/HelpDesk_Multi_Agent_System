from elasticsearch import Elasticsearch

es = Elasticsearch(
    "http://localhost:9200",  # or your ES_HOST
)

# Get all indices except system indices (those starting with '.')
indices = [idx for idx in es.indices.get_alias(index="*") if not idx.startswith(".")]

for idx in indices:
    print(f"Deleting index: {idx}")
    es.indices.delete(index=idx)
print("All user indices deleted.")