import os
from typing import List
from openai import OpenAI
from .prompts.prompt import generate_final_summary
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")
client = OpenAI(
    api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

import logging

logger = logging.getLogger(__name__)


def combine_chunk_summaries(summaries: List[str], summary_type: str) -> str:
    """Creates a final summary from a list of chunk summaries using Gemini API.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        summaries (List[str]): The list of chunk summaries to combine.
        summary_type (str): The type of summary to generate.

    Returns:
        str: The final combined summary
    """
    logger.error("SONO ENTRATOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO")
    # Join the summaries with a newline and a separator
    combined_text = "\n\n--- SUMMARY CHUNK ---\n\n".join(summaries)

    # Get the appropriate prompt for this summary type and situation
    # We're combining multiple summaries, so text_was_splitted is True
    prompt = generate_final_summary(summary_type, text_was_splitted=True)

    # Create the full prompt with the combined summaries
    full_prompt = f"""
    {prompt}
    
    {combined_text}
    """

    # Call the Gemini API to actually create the final summary
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a math syntax expert."},
            {"role": "user", "content": full_prompt},
        ],
    )

    # Return the actual final summary, not just the prompt
    return response.choices[0].message.content
