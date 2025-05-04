
import os, sys
sys.path.append(os.path.abspath(os.path.join(__file__, "../../..")))    
from SummarizationAgent.tools.chunker.chunker_types.cosine_chuncker import chunk_document_cosine
from SummarizationAgent.tools.chunker.chunker_types.embedder import Embedder
import time
import json
import logging
from uuid import uuid4
import requests
from dotenv import load_dotenv
from typing import List
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()


class UploadInKB:

    def __init__(self, user_id) -> None:
        self.qdrant_host=os.getenv("QDRANT_HOST")
        self.qdrant_headers={
            "api-key": os.getenv("QDRANT_API_KEY"),               
            "Content-Type": "application/json"
        }
        self.user_id = user_id
        self.collection_name = self._get_or_create_user_collection()
        self.embedder = Embedder()

    def _get_or_create_user_collection(self)->str:
        name = f"RAG_user{self.user_id}"
        try:
            # get existing collections
            url_list = f"{self.qdrant_host}/collections"
            resp = requests.get(url_list, headers=self.qdrant_headers)
            resp.raise_for_status()
            collections = resp.json()["result"]["collections"]
            existing_names = {col["name"] for col in collections}

            # if note present create collection for a specific user (Cosine Distance)
            if name not in existing_names:
                logger.info(f"Creating Qdrant collection `{name}`")
                url_create = f"{self.qdrant_host}/collections/{name}"
                payload = {
                    "vectors": {
                        "size": 768, # embedding size for text-embedding-004
                        "distance": "Cosine"
                    }
                }
                resp = requests.put(url_create, headers=self.qdrant_headers, json=payload)
                resp.raise_for_status()
                
                # create index for filterings
                index_url = f"{self.qdrant_host}/collections/{name}/index"
                index_payload = {
                    "field_name": "user_id",
                    "field_schema": "keyword"
                }
                resp = requests.put(index_url, headers=self.qdrant_headers, json=index_payload)
                resp.raise_for_status()
                logger.info(f"Created payload index for `user_id` in collection `{name}`")
        except Exception:
            logger.exception("Error checking or creating Qdrant collection")
            raise

        return name

    def upload_in_kb(self, text:str) -> None:
        """
        Upload the text in the knowledge base
        """
        try:
            chunks_with_embedding = chunk_document_cosine(text, return_embedding=True)
            #print(chunks_with_embedding)
            points = []
            for cwe in chunks_with_embedding:
                pid = uuid4().hex
                points.append({
                    "id":     pid,
                    "vector": cwe['embedding'],
                    "payload": {
                        "user_id": self.user_id,
                        "page_content": cwe['section'],
                        "ts": int(time.time())
                    }
                })

            if points:
                upsert_url = f"{self.qdrant_host}/collections/{self.collection_name}/points?wait=true"
                resp = requests.put(upsert_url, headers=self.qdrant_headers, json={"points": points})
                resp.raise_for_status()
                logger.info("Upserted %d points (new+updated)", len(points))
        except Exception:
            logger.exception("Error uploading text in Qdrant collection")

    def retrieve_relevant_knowledge(self, query: str, top_k: int = 5) -> List[str]:
        # embed query
        query_embedding=self.embedder.embed(query)
        # search payload
        search_payload = {
            "vector": query_embedding,
            "limit": top_k,
            "with_payload": True,
            "filter": {
                "must": [
                    {
                        "key": "user_id",
                        "match": {"value": self.user_id}
                    }
                ]
            }
        }
        #send request
        search_url = f"{self.qdrant_host}/collections/{self.collection_name}/points/search"
        resp = requests.post(search_url, headers=self.qdrant_headers, json=search_payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
                logger.error("Qdrant API error response: %s", resp.text)
                raise
        hits = resp.json()["result"]
        # relevance results
        return [hit["payload"]["page_content"] for hit in hits]


    
