import os
from typing import Any, Dict, List, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from src.utils.logger import logger

class ElasticsearchService:
    """
    Service class for managing Elasticsearch operations in a scalable, professional way.
    Handles connection, CRUD operations, and error management.
    """
    _client: Optional[Elasticsearch] = None

    def __init__(self, index: Optional[str] = None):
        self.host = os.getenv('ES_HOST', 'http://localhost:9200')
        self.user = os.getenv('ES_USER', 'elastic')
        self.password = os.getenv('ES_PASS', 'changeme')
        self.index = index or os.getenv('ES_INDEX', 'tickets')
        self._ensure_client()

    @classmethod
    def _ensure_client(cls):
        if cls._client is None:
            try:
                cls._client = Elasticsearch(
                    os.getenv('ES_HOST', 'http://localhost:9200'),
                    basic_auth=(os.getenv('ES_USER', 'elastic'), os.getenv('ES_PASS', 'changeme'))
                )
                logger.info("Elasticsearch client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Elasticsearch client: {e}")
                raise

    @property
    def client(self) -> Elasticsearch:
        self._ensure_client()
        return self._client

    def index_document(self, document: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """
        Index (create or update) a document in Elasticsearch.
        :param document: The document to index
        :param doc_id: Optional document ID
        :return: The document ID
        """
        try:
            resp = self.client.index(index=self.index, id=doc_id, document=document)
            logger.debug(f"Indexed document in {self.index}: {resp['_id']}")
            return resp['_id']
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID from Elasticsearch.
        :param doc_id: The document ID
        :return: The document as a dict, or None if not found
        """
        try:
            resp = self.client.get(index=self.index, id=doc_id)
            return resp['_source']
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in {self.index}.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {e}")
            raise

    def search_documents(self, query: Dict[str, Any], size: int = 1000) -> List[Dict[str, Any]]:
        """
        Search for documents in Elasticsearch.
        :param query: The Elasticsearch query DSL
        :param size: Max number of results
        :return: List of document sources
        """
        try:
            resp = self.client.search(index=self.index, body={"query": query}, size=size)
            hits = resp.get('hits', {}).get('hits', [])
            return [hit['_source'] for hit in hits]
        except Exception as e:
            if hasattr(e, 'status_code') and e.status_code == 404 and 'index_not_found_exception' in str(e):
                logger.info(f"No index [{self.index}] found in Elasticsearch. Returning empty result.")
            else:
                logger.error(f"Error searching documents: {e}")
            raise

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID from Elasticsearch.
        :param doc_id: The document ID
        :return: True if deleted, False if not found
        """
        try:
            self.client.delete(index=self.index, id=doc_id)
            logger.debug(f"Deleted document {doc_id} from {self.index}.")
            return True
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found for deletion in {self.index}.")
            return False
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            raise

    def delete_all_documents(self):
        """
        Delete all documents in the index.
        """
        self.client.delete_by_query(index=self.index, body={"query": {"match_all": {}}})
        logger.info(f"Deleted all documents from {self.index}") 