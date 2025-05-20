

import os, sys


from .utils import chunk_text
import time
import json
import logging
from uuid import uuid4
import requests
from dotenv import load_dotenv
from typing import List
from google import genai
from google.genai import types
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()


class Embedder:
    def __init__(self) -> None:
        self.embedding_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


    def embed(self, text: str) -> List[float]:
        """
        Embed the text using the embedder API
        """
        result = self.embedding_client.models.embed_content(
                model="models/text-embedding-004",
                contents=[text],
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
            )
        return result.embeddings[0].values

class UploadInfo:

    def __init__(self, user_id) -> None:
        self.qdrant_host = os.getenv("QDRANT_HOST")
        self.qdrant_headers = {
            "api-key": os.getenv("QDRANT_API_KEY"),
            "Content-Type": "application/json",
        }
        #self.user_id = user_id
        #self.collection_name = self._get_or_create_user_collection()
        #print("RAG_COLLECTION_NAME:", self.collection_name)
        self.embedder = Embedder()

    def _get_or_create_user_collection(self, user_id="RAG_usertest_user") -> str:
        name = f"{user_id}"
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
                        "size": 768,  # embedding size for text-embedding-004
                        "distance": "Cosine",
                    }
                }
                resp = requests.put(
                    url_create, headers=self.qdrant_headers, json=payload
                )
                resp.raise_for_status()

                # create index for filterings
                index_url = f"{self.qdrant_host}/collections/{name}/index"
                index_payload = {"field_name": "user_id", "field_schema": "keyword"}
                resp = requests.put(
                    index_url, headers=self.qdrant_headers, json=index_payload
                )
                resp.raise_for_status()
                logger.info(
                    f"Created payload index for `user_id` in collection `{name}`"
                )
        except Exception:
            logger.exception("Error checking or creating Qdrant collection")
            raise

        return name

    def upload_in_kb(self, text: str, user_id="RAG_usertest_user") -> None:
        collection_name = self._get_or_create_user_collection() 
        """
        Upload the text in the knowledge base
        """
        try:
            chunks = chunk_text(text)
            points = []
            for chunk in chunks:
                pid = uuid4().hex                
                points.append(
                    {
                        "id": pid,
                        "vector": self.embedder.embed(chunk),
                        "payload": {
                            "user_id": user_id,
                            "page_content": chunk,
                            "ts": int(time.time()),
                        },
                    }
                )

            if points:
                upsert_url = f"{self.qdrant_host}/collections/{collection_name}/points?wait=true"
                resp = requests.put(
                    upsert_url, headers=self.qdrant_headers, json={"points": points}
                )
                resp.raise_for_status()
                logger.info("Upserted %d points (new+updated)", len(points))
        except Exception:
            logger.exception("Error uploading text in Qdrant collection")