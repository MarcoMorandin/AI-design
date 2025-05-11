from .prompts.prompt import generate_final_summary
import json
from dotenv import load_dotenv
import os
import requests

load_dotenv()

grok_chat_url="https://api.groq.com/openai/v1/chat/completions"
grok_api_key=os.getenv("GROQ_API_KEY")

def get_final_summary(all_chunks_text_to_summarize:str, summary_type: str, text_was_splitted:bool) -> str:
    """Put togheter summaries of different chunks:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        all_chunks_text_to_summarize (str): The input text that needs to be summarized (the text about all the chunks that need to be summarized).
        summary_type (str): The type of summary to generate.
        text_was_splitted (bool): Whether the orignal text was splitted or not (If came from different chunks). (True or False)

    Returns:
        str: Prompt to summarize a text
    """
    SYSTEM_PROMPT= generate_final_summary(summary_type, text_was_splitted)
    system = SYSTEM_PROMPT
    user_payload = {
        "text_to_be_summarized": all_chunks_text_to_summarize
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