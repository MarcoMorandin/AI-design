from .prompts.prompt import fix_formulas_prompt
import json
from dotenv import load_dotenv
import os
import requests

load_dotenv()

grok_chat_url="https://api.groq.com/openai/v1/chat/completions"
grok_api_key=os.getenv("GROQ_API_KEY")

def get_correct_format(text_to_correct_format: str) -> str:
    """
    Get the correct formatting for a text.

    Args:
        text_to_correct_format (str): The input text that needs to be corrected and formatted.

    Returns:
        str: The formatted and corrected text.
    """
    SYSTEM_PROMT= fix_formulas_prompt()
    system = SYSTEM_PROMT
    user_payload = {
        "text_to_format": text_to_correct_format
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