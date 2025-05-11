from .prompts.prompt import summary_prompt
from .prompts.prompt import fix_formulas_prompt
import json
from dotenv import load_dotenv
import os
import requests

load_dotenv()

grok_chat_url="https://api.groq.com/openai/v1/chat/completions"
grok_api_key=os.getenv("GROQ_API_KEY")


def summarize_chunk(chunk_to_summarize:str, summary_type: str="technical") -> str:
    """Summarize the provided text choosing among this four summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        chunk_to_summarize (str): The input text that needs to be summarized.
        summary_type (str): The type of summary to generate.


    Returns:
        str: Summary of the chunk
    """
    SYSTEM_PROMPT= summary_prompt(summary_type)
    system = SYSTEM_PROMPT
    user_payload = {
        "chunk_to_summarize": chunk_to_summarize
    }

    messages = [
        {"role": "system",  "content": system},
        {"role": "user",    "content": json.dumps(user_payload)}
    ]

    resp = requests.post(
        grok_chat_url,
        headers={
            "Authorization": f"Bearer {grok_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.0
        }
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return content