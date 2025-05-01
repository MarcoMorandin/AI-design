import os
import time
import json
import logging
from uuid import uuid4
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

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
        name = f"user_{self.user_id}"
        try:
            # 1) List existing collections
            url_list = f"{self.qdrant_host}/collections"
            resp = requests.get(url_list, headers=self.qdrant_headers)
            resp.raise_for_status()
            collections = resp.json()["result"]["collections"]
            existing_names = {col["name"] for col in collections}

            # 2) If not found, create with COSINE distance
            if name not in existing_names:
                logger.info(f"Creating Qdrant collection `{name}`")
                url_create = f"{self.qdrant_host}/collections/{name}"
                payload = {
                    "vectors": {
                        "size": 768,                    # embedding dim for text-embedding-004
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


    def insert_into_long_memory(self, chat_history: str):
        """Extract structured preferences, embed their descriptions, and store each."""
        memories = self._create_momories_from_chat(chat_history)
        if memories == "NO_PREFERENCE":
            logger.info("No preferences found—nothing to insert")
            return

        points = []
        for pref in memories:
            topic = pref.get("topic")
            desc = pref.get("description")
            if not topic or not desc:
                logger.warning("Skipping malformed preference entry: %r", pref)
                continue

            try:
                emb = self._get_embedding(desc)
            except Exception:
                logger.exception("Embedding failed for: %s", desc)
                continue

            point = {
                "id": uuid4().hex,
                "payload": {
                    "user_id": self.user_id,
                    "topic": topic,
                    "description": desc,
                    "ts": int(time.time()),
                },
                "vector": emb,
            }
            points.append(point)

        if not points:
            logger.info("No valid preference memories to upsert")
            return

        try:
            upsert_url = f"{self.qdrant_host}/collections/{self.collection_name}/points?wait=true"
            body = {"points": points}
            resp = requests.put(upsert_url, headers=self.qdrant_headers, json=body)
            resp.raise_for_status()
            logger.info("Upserted %d points into `%s`", len(points), self.collection_name)
        except Exception:
            logger.exception("Failed to upsert points into Qdrant")

    def _create_momories_from_chat(self, chat_history):
        """Call the GROQ Chat API to extract a list of {topic,description} or 'NO_PREFERENCE'."""
        system_prompt = self._get_qrok_system_prompt()
        messages = [
        {"role": "system",  "content": system_prompt},
        {"role": "user",    "content": chat_history}
        ]

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = requests.post(
                self.grok_chat_url,
                headers={
                    "Authorization": f"Bearer {self.grok_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
        except Exception:
            logger.exception("GROQ Chat API call failed")
            return "NO_PREFERENCE"

        # If the model returned the string, it'll come through as the value
        prefs = data.get("preferences")
        if prefs == "NO_PREFERENCE" or not prefs:
            return "NO_PREFERENCE"
        return prefs
        

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
    
    def _get_qrok_system_prompt(self):
        system_prompt = (
            "You are an assistant whose sole job is to extract user preferences from a chat conversation."
            "If the preferences are about the same macro topi, put them together."
            "You should also get information about user that can be usefull for an AI agent (followig exactly the same structure of the preferences)"
            "You will receive the entire chat history as a single string. "
            "Analyze it and respond with a single, well-formatted JSON object with exactly one field: \"preferences\". "
            "The value of \"preferences\" must be either:\n"
            "  • A list of preference objects, where each object has exactly two fields:\n"
            "      – \"topic\": a label for the general area of preference (e.g. \"genre\", \"cuisine\").\n"
            "      – \"description\": a comprenshicve description of the user preferences.\n"
            "  • The string \"NO_PREFERENCE\" (without quotes) if the user expressed no preferences in the chat.\n"
            "Do not include any other fields, explanations, or formatting—only the JSON object."
        )
        return system_prompt


def main():
    # 3) Instantiate for a user
    lm = LongMemory(user_id="test_user")

    # 4) Define a fake chat history
    chat = (
    "User: Hey, I spent the weekend diving into that article on sustainable urban gardening you recommended.\n"
    "Assistant: Fantastic! What stood out to you the most?\n"
    "User: Well, the benefits to local ecosystems were eye-opening, and I liked how it covered both container gardening and rooftop plots.\n"
    "Assistant: Got it—ecosystem impact plus container vs. rooftop distinctions.\n"
    "User: Exactly. Now, I could read another ten pages on methods, but I usually skim for the core ideas first.\n"
    "Assistant: Understood, you’d like the main takeaways up front.\n"
    "User: Right—and honestly, big paragraphs tend to blur together for me. Short, sharp points really help.\n"
    "Assistant: So bullet-style highlights rather than long blocks?\n"
    "User: Yeah, a quick list of the key steps with maybe a one-sentence note on each—that’s perfect.\n"
    "Assistant: Great—I’ll put that together for you.\n"
)


    # 5) Insert into memory
    print("→ Inserting preferences into LongMemory…")
    lm.insert_into_long_memory(chat)

    # 6) Query back those memories
    print("→ Querying memories for 'what does the user like?'")
    results = lm.get_memories("What does the user like?", top_k=5)
    
    print("\nRetrieved memories:")
    for idx, mem in enumerate(results, 1):
        print(f"{idx}. [{mem['topic']}] {mem['description']} (score={mem['score']:.3f})")

if __name__ == "__main__":
    main()