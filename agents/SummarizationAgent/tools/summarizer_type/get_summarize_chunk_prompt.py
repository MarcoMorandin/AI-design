from typing import List
import os
from openai import OpenAI
from .prompts.prompt import summary_prompt
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")
client = OpenAI(
    api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

import logging

logger = logging.getLogger(__name__)


def summarise_chunk(text: str, summary_type: str = "technical") -> str:
    """Summarizes a chunk of text using Gemini API.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        text (str): The text chunk to summarize.
        summary_type (str): The type of summary to generate.

    Returns:
        str: The summarized text, not just a prompt
    """
    # Get the appropriate prompt for this summary type
    prompt = summary_prompt(summary_type)

    # Create the full prompt with the input text
    full_prompt = f"""
    {prompt}
    
    --- TEXT TO SUMMARIZE ---
    {text}
    --- TEXT TO SUMMARIZE ---
    """

    # Call the Gemini API to actually summarize the text
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a math syntax expert."},
            {"role": "user", "content": full_prompt},
        ],
    )

    # Return the actual summary, not just the prompt
    return response.choices[0].message.content


def summarize_chunks(chunks: List[str], summary_type: str = "technical") -> List[str]:
    """Summarizes a list of text chunks using Gemini API.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        chunks (List[str]): The list of text chunks to summarize.
        summary_type (str): The type of summary to generate.

    Returns:
        List[str]: A list of summarized texts
    """
    summaries = []

    for chunk in chunks:
        # Summarize each chunk
        summary = summarise_chunk(chunk, summary_type)
        summaries.append(summary)

    return summaries
