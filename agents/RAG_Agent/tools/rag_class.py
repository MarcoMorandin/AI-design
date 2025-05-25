import os
from .utils import chunk_text
import time
import logging
from uuid import uuid4
import requests
from dotenv import load_dotenv
from typing import List
from google import genai
from google.genai import types

# logger
logger = logging.getLogger(__name__)

load_dotenv()

class Embedder:
    """
    A class for generating text embeddings using Google's Gemini API.
    """
    def __init__(self) -> None:
        """
        Initialize the Embedder with the Gemini API client.
        """
        self.embedding_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def embed(self, text: str) -> List[float]:
        """
        Embed the text using the embedder API.
        
        Args:
            text (str): The text to be embedded.
            
        Returns:
            List[float]: A vector representation of the input text.
        """
        result = self.embedding_client.models.embed_content(
            model="models/text-embedding-004",
            contents=[text],
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
        )
        return result.embeddings[0].values


class RAG:
    """
    Retrieval-Augmented Generation (RAG) class that manages knowledge base operations.
    This class handles storing, retrieving, and managing text data in a vector database.
    """

    def __init__(self, user_id) -> None:
        """
        Initialize the RAG system for a specific user.
        
        Args:
            user_id (str): The unique identifier for the user.
        """
        self.qdrant_host = os.getenv("QDRANT_HOST")
        self.qdrant_headers = {
            "api-key": os.getenv("QDRANT_API_KEY"),
            "Content-Type": "application/json",
        }
        self.user_id = user_id
        self.collection_name = self._get_or_create_user_collection()
        print("RAG_COLLECTION_NAME:", self.collection_name)
        self.embedder = Embedder()

    def _get_or_create_user_collection(self) -> str:
        """
        Get an existing collection for the user or create a new one if it doesn't exist.
        
        Returns:
            str: The name of the user's collection.
            
        Raises:
            Exception: If there's an error checking or creating the Qdrant collection.
        """
        name = f"{self.user_id}"
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

    def upload_in_kb(self, text: str) -> None:
        """
        Upload the text to the knowledge base after chunking and embedding.
        
        Args:
            text (str): The text to be uploaded to the knowledge base.
            
        Raises:
            Exception: If there's an error uploading text to the Qdrant collection.
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
                            "user_id": self.user_id,
                            "page_content": chunk,
                            "ts": int(time.time()),
                        },
                    }
                )

            if points:
                upsert_url = f"{self.qdrant_host}/collections/{self.collection_name}/points?wait=true"
                resp = requests.put(
                    upsert_url, headers=self.qdrant_headers, json={"points": points}
                )
                resp.raise_for_status()
                logger.info("Upserted %d points (new+updated)", len(points))
        except Exception:
            logger.exception("Error uploading text in Qdrant collection")

    def retrieve_relevant_knowledge(self, query: str, top_k: int = 5) -> List[str]:
        """
        Retrieve the most relevant knowledge from the database based on the query.
        
        Args:
            query (str): The query text to search for relevant information.
            top_k (int, optional): The number of top results to return. Defaults to 5.
            
        Returns:
            List[str]: A list of text chunks that are most relevant to the query.
            
        Raises:
            requests.exceptions.HTTPError: If there's an error in the Qdrant API response.
        """
        # embed query
        query_embedding = self.embedder.embed(query)
        # search payload
        search_payload = {
            "vector": query_embedding,
            "limit": top_k,
            "with_payload": True,
        }
        # send request
        search_url = (
            f"{self.qdrant_host}/collections/{self.collection_name}/points/search"
        )
        resp = requests.post(
            search_url, headers=self.qdrant_headers, json=search_payload
        )
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            logger.error("Qdrant API error response: %s", resp.text)
            raise
        hits = resp.json()["result"]
        # relevance results
        return [hit["payload"]["page_content"] for hit in hits]

    def get_all_contents(self) -> List[str]:
        """
        Retrieve all 'page_content' fields for the current user from the collection.
        
        Returns:
            List[str]: A list of all text chunks stored for the current user.
            
        Raises:
            requests.exceptions.HTTPError: If there's an error in the Qdrant API response.
        """
        contents = []
        scroll_url = (
            f"{self.qdrant_host}/collections/{self.collection_name}/points/scroll"
        )
        scroll_payload = {
            "with_payload": True,
            "with_vector": False,
            "limit": 100,  # Adjust as needed for batch size
        }
        next_page = None

        while True:
            if next_page:
                scroll_payload["offset"] = next_page
            resp = requests.post(
                scroll_url, headers=self.qdrant_headers, json=scroll_payload
            )
            resp.raise_for_status()
            data = resp.json()["result"]
            for point in data["points"]:
                payload = point.get("payload", {})
                if "page_content" in payload:
                    contents.append(payload["page_content"])
            if not data.get("next_page_offset"):
                break
            next_page = data["next_page_offset"]

        return contents

