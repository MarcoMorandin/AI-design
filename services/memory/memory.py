import os
import time
import json
import logging
from uuid import uuid4
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv
from utils.system_prompt import SYSTEM_PROMT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

class LongMemory():

    def __init__(self, user_id):
        self.user_id = user_id

        self.qdrant_host=os.getenv("QDRANT_HOST")
        self.qdrant_headers={
            "api-key": os.getenv("QDRANT_API_KEY"),               
            "Content-Type": "application/json"
        }
        
        self.embedding_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
        self.grok_chat_url="https://api.groq.com/openai/v1/chat/completions"
        self.grok_api_key=os.getenv("GROQ_API_KEY")

        self.collection_name = self._get_or_create_user_collection()
        

    def _get_or_create_user_collection(self)->str:
        name = f"user_long_memory{self.user_id}"
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

    def _scroll_current_preferences(self) -> list[dict]:
        """Fetch all existing prefs for this user via the REST scroll API."""
        url = f"{self.qdrant_host}/collections/{self.collection_name}/points/scroll"
        body = {
            "filter": {
                "must": [
                    {"key": "user_id", "match": {"value": self.user_id}}
                ]
            },
            "with_payload": True,
            "limit": 50
        }
        resp = requests.post(url, headers=self.qdrant_headers, json=body)
        resp.raise_for_status()
        pts = resp.json()["result"]["points"]
        return [
            {
                "id":          pt["id"],
                "topic":       pt["payload"]["topic"],
                "description": pt["payload"]["description"]
            }
            for pt in pts
        ]

    def insert_into_long_memory_with_update(self, chat_history: str):
        # current preferences
        current_prefs = self._scroll_current_preferences()

        # get nre preferences
        new_prefs = self._extract_preferences(
            chat_history=chat_history,
            existing_prefs=current_prefs
        )

        if new_prefs == "NO_PREFERENCE":
            logger.info("No preferences found—nothing to insert/update")
            return

        # update point in db
        points = []
        for pref in new_prefs:
            topic = pref.get("topic")
            desc  = pref.get("description")
            pid   = pref.get("id") or uuid4().hex    # use provided id or generate new

            if not topic or not desc:
                logger.warning("Skipping malformed pref: %r", pref)
                continue

            emb = None
            try:
                emb = self._get_embedding(desc)
            except Exception:
                logger.exception("Embedding failed for: %s", desc)
                continue

            points.append({
                "id":     pid,
                "vector": emb,
                "payload": {
                    "user_id":     self.user_id,
                    "topic":       topic,
                    "description": desc,
                    "ts":          int(time.time())
                }
            })

        if points:
            upsert_url = f"{self.qdrant_host}/collections/{self.collection_name}/points?wait=true"
            resp = requests.put(upsert_url, headers=self.qdrant_headers, json={"points": points})
            resp.raise_for_status()
            logger.info("Upserted %d points (new+updated)", len(points))


    def _get_embedding(self, text):
        """Call Google embed_content, return the embedding vector."""
        try:
            result = self.embedding_client.models.embed_content(
                model="models/text-embedding-004",
                contents=[text],
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
            )
            return result.embeddings[0].values
        except Exception:
            logger.exception("Failed to get embedding for text: %s", text)
            raise Exception("Failed to get embedding")

    def get_memories(self, query:str, top_k:int=5, max_cosine_distance:float=0.7):
        """Retrieve and filter the most relevant memories by cosine distance."""
        try:
            q_emb = self._get_embedding(query)
            query_url = f"{self.qdrant_host}/collections/{self.collection_name}/points/query"
            query_body = {
                "query": q_emb,                  
                "top": top_k,
                "with_payload": True,            # include payload in response
                "filter": {
                    "must": [
                        {"key": "user_id", "match": {"value": self.user_id}}
                    ]
                }
            }
            resp = requests.post(query_url, headers=self.qdrant_headers, json=query_body)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error("Qdrant API error response: %s", resp.text)
                raise
            points = resp.json()["result"]["points"]
        except Exception:
            logger.exception("Failed to query points for `%s`", query)
            return []

        results = []
        for pt in points:
            if pt["score"] <= max_cosine_distance:
                results.append({
                    "id": pt["id"],
                    "topic": pt["payload"].get("topic"),
                    "description": pt["payload"].get("description"),
                    "score": pt["score"]
                })
        logger.info("Retrieved %d memories", len(results))
        return results
    
    def _extract_preferences(self, chat_history: str, existing_prefs: list[dict]):
        """Ask the LLM to merge chat hints with existing prefs, tagging with 'id' when updating."""
        system = SYSTEM_PROMT
        user_payload = {
            "existing_preferences": existing_prefs,
            "chat_history":         chat_history
        }

        messages = [
            {"role": "system",  "content": system},
            {"role": "user",    "content": json.dumps(user_payload)}
        ]

        resp = requests.post(
            self.grok_chat_url,
            headers={
                "Authorization": f"Bearer {self.grok_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)

        prefs = data.get("preferences")
        if prefs == "NO_PREFERENCE" or not prefs:
            return "NO_PREFERENCE"
        return prefs

def main():
    lm = LongMemory(user_id="test_user")

    chat = (
    "User: Hey, I spent the weekend diving into that article on sustainable urban gardening you recommended.\n"
    "Assistant: Fantastic! What stood out to you the most?\n"
    "User: Well, the benefits to local ecosystems were eye-opening, and I liked how it covered only container gardening.\n"
    "Assistant: Got it—ecosystem impact plus container vs. rooftop distinctions.\n"
    "User: Exactly. Now, I could read another ten pages on methods, but I usually skim for the core ideas first.\n"
    "Assistant: Understood, you’d like the main takeaways up front.\n"
    "User: Right—and honestly, I want longer paragraph.\n"
    "Assistant: Great—I’ll put that together for you.\n"
    "User: I really prefer have a technical summary for scientific subject\n"
)


    print("→ Inserting preferences into LongMemory…")
    lm.insert_into_long_memory_with_update(chat)


    print("→ Querying memories for 'what does the user like?'")
    results = lm.get_memories("What does the user like?", top_k=5)
    
    print("\nRetrieved memories:")
    for idx, mem in enumerate(results, 1):
        print(f"{idx}. [{mem['topic']}] {mem['description']} (score={mem['score']:.3f})")

if __name__ == "__main__":
    main()