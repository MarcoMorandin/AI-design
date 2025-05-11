from google import genai
from google.genai import types
from ..core.config import settings


class Embedder:

    def __init__(self) -> None:
        self.llm_client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def get_token_count(self, chunk: str) -> int:
        return self.llm_client.models.count_tokens(model=settings.GEMINI_MODEL_NAME, contents=chunk)

    def embed(self, chunk):
        result = self.llm_client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=chunk,
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
        )
        return result.embeddings[0].values
