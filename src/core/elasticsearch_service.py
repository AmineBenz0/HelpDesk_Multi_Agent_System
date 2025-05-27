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
        self.host = os.getenv('ES_HOST', 'http://helpdesk_elasticsearch:9200')
        self.user = os.getenv('ES_USER', 'elastic')
        self.password = os.getenv('ES_PASS', 'changeme')
        self.index = index or os.getenv('ES_INDEX', 'tickets')
        self._ensure_client()

    @classmethod
    def _ensure_client(cls):
        if cls._client is None:
            try:
                cls._client = Elasticsearch(
                    os.getenv('ES_HOST', 'http://helpdesk_elasticsearch:9200'),
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

    def index_document(self, document: Dict[str, Any], doc_id: Optional[str] = None, index: Optional[str] = None) -> str:
        """
        Index (create or update) a document in Elasticsearch.
        :param document: The document to index
        :param doc_id: Optional document ID
        :param index: Optional index name to override the default
        :return: The document ID
        """
        try:
            target_index = index or self.index
            resp = self.client.index(index=target_index, id=doc_id, document=document)
            logger.debug(f"Indexed document in {target_index}: {resp['_id']}")
            return resp['_id']
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            raise

    def get_document(self, doc_id: str, index: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID from Elasticsearch.
        :param doc_id: The document ID
        :param index: Optional index name to override the default
        :return: The document as a dict, or None if not found
        """
        try:
            target_index = index or self.index
            resp = self.client.get(index=target_index, id=doc_id)
            return resp['_source']
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found in {target_index}.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {e}")
            raise

    def search_documents(self, query: Dict[str, Any], size: int = 1000, index: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for documents in Elasticsearch.
        :param query: The Elasticsearch query DSL
        :param size: Max number of results
        :param index: Optional index name to override the default
        :return: List of document sources
        """
        try:
            target_index = index or self.index
            resp = self.client.search(index=target_index, body={"query": query}, size=size)
            hits = resp.get('hits', {}).get('hits', [])
            return [hit['_source'] for hit in hits]
        except Exception as e:
            target_index = index or self.index
            if hasattr(e, 'status_code') and e.status_code == 404 and 'index_not_found_exception' in str(e):
                logger.info(f"No index [{target_index}] found in Elasticsearch. Returning empty result.")
            else:
                logger.error(f"Error searching documents: {e}")
            raise

    def delete_document(self, doc_id: str, index: Optional[str] = None) -> bool:
        """
        Delete a document by ID from Elasticsearch.
        :param doc_id: The document ID
        :param index: Optional index name to override the default
        :return: True if deleted, False if not found
        """
        try:
            target_index = index or self.index
            self.client.delete(index=target_index, id=doc_id)
            logger.debug(f"Deleted document {doc_id} from {target_index}.")
            return True
        except NotFoundError:
            target_index = index or self.index
            logger.warning(f"Document {doc_id} not found for deletion in {target_index}.")
            return False
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            raise

    def delete_all_documents(self, index: Optional[str] = None):
        """
        Delete all documents in the index.
        :param index: Optional index name to override the default
        """
        target_index = index or self.index
        self.client.delete_by_query(index=target_index, body={"query": {"match_all": {}}})
        logger.info(f"Deleted all documents from {target_index}")
        
    def create_index_if_not_exists(self, index: Optional[str] = None, mappings: Optional[Dict] = None):
        """
        Create an index if it doesn't exist.
        :param index: Optional index name to override the default
        :param mappings: Optional mappings for the index
        """
        target_index = index or self.index
        try:
            if not self.client.indices.exists(index=target_index):
                body = {}
                if mappings:
                    body["mappings"] = mappings
                self.client.indices.create(index=target_index, body=body)
                logger.info(f"Created index {target_index}")
            else:
                logger.debug(f"Index {target_index} already exists")
        except Exception as e:
            logger.error(f"Error creating index {target_index}: {e}")
            raise 