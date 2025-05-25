import os
import time
import json
import logging
from uuid import uuid4
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv
from typing import List, Dict, Union
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()


class LongMemory:

    def __init__(self, user_id, memory_prompt):
        self.user_id = user_id
        self.memory_prompt = memory_prompt

        self.qdrant_host = os.getenv("QDRANT_HOST")
        self.qdrant_headers = {
            "api-key": os.getenv("QDRANT_API_KEY"),
            "Content-Type": "application/json",
        }

        self.embedding_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_client = OpenAI(
            api_key=self.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.collection_name = self._get_or_create_user_collection()

    def _get_or_create_user_collection(self) -> str:
        name = f"user_long_memory_{self.user_id}"
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

    def _scroll_current_memories(self) -> list[dict]:
        """Fetch all existing memories for this user via the REST scroll API."""
        url = f"{self.qdrant_host}/collections/{self.collection_name}/points/scroll"
        body = {
            "filter": {"must": [{"key": "user_id", "match": {"value": self.user_id}}]},
            "with_payload": True,
            "limit": 50,
        }
        resp = requests.post(url, headers=self.qdrant_headers, json=body)
        resp.raise_for_status()
        pts = resp.json()["result"]["points"]
        result = [
            {
                "id": pt["id"],
                "topic": pt["payload"]["topic"],
                "description": pt["payload"]["description"],
            }
            for pt in pts
        ]
        if len(result) > 0:
            return result
        else:
            return []

    def insert_into_long_memory_with_update(
        self, chat_history: Union[str, List[Dict[str, str]]]
    ):

        # the chat history could also be a list of dicts
        if isinstance(chat_history, list):
            chat_history_payload = json.dumps(chat_history, ensure_ascii=False)
        else:
            chat_history_payload = chat_history

        # current memories
        current_memories = self._scroll_current_memories()
        # get new memories
        new_memories = self._extract_memories(
            chat_history=chat_history_payload, existing_memories=current_memories
        )

        if new_memories == "NO_MEMORIES_TO_ADD":
            logger.info("No memories should be added or updated")
            return

        # update point in db
        points = []
        for memory in new_memories:
            topic = memory.get("topic")
            desc = memory.get("description")
            pid = memory.get("id") or uuid4().hex  # use provided id or generate new

            if not topic or not desc:
                logger.warning("Skipping malformed memory: %r", memory)
                continue

            emb = None
            try:
                emb = self._get_embedding(desc)
            except Exception:
                logger.exception("Embedding failed for: %s", desc)
                continue

            points.append(
                {
                    "id": pid,
                    "vector": emb,
                    "payload": {
                        "user_id": self.user_id,
                        "topic": topic,
                        "description": desc,
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

    def _get_embedding(self, text):
        """Call Google embed_content, return the embedding vector."""
        try:
            result = self.embedding_client.models.embed_content(
                model="models/text-embedding-004",
                contents=[text],
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            return result.embeddings[0].values
        except Exception:
            logger.exception("Failed to get embedding for text: %s", text)
            raise Exception("Failed to get embedding")

    def get_memories(
        self, query: str, top_k: int = 5, max_cosine_distance: float = 0.7
    ):
        """Retrieve and filter the most relevant memories by cosine distance."""
        try:
            q_emb = self._get_embedding(query)
            query_url = (
                f"{self.qdrant_host}/collections/{self.collection_name}/points/query"
            )
            query_body = {
                "query": q_emb,
                "top": top_k,
                "with_payload": True,  # include payload in response
                "filter": {
                    "must": [{"key": "user_id", "match": {"value": self.user_id}}]
                },
            }
            resp = requests.post(
                query_url, headers=self.qdrant_headers, json=query_body
            )
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError:
                logger.error("Qdrant API error response: %s", resp.text)
                raise
            points = resp.json()["result"]["points"]
        except Exception:
            logger.exception("Failed to query points for `%s`", query)
            return []

        results = []
        for pt in points:
            if pt["score"] <= max_cosine_distance:
                results.append(
                    {
                        "id": pt["id"],
                        "topic": pt["payload"].get("topic"),
                        "description": pt["payload"].get("description"),
                        "score": pt["score"],
                    }
                )
        logger.info("Retrieved %d memories", len(results))
        return results

    def _extract_memories(self, chat_history: str, existing_memories: list[dict]):
        """Ask the LLM to merge chat hints with existing memories, tagging with 'id' when updating."""

        user_payload = {
            "existing_memories": existing_memories,
            "chat_history": chat_history,
        }

        messages = [
            {"role": "system", "content": self.memory_prompt},
            {"role": "user", "content": json.dumps(user_payload)},
        ]

        try:
            response = self.openai_client.chat.completions.create(
                model="gemini-2.0-flash",
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            memories = data.get("memories_to_add")
            if memories == "NO_MEMORIES_TO_ADD" or not memories:
                return "NO_MEMORIES_TO_ADD"
            return memories

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
