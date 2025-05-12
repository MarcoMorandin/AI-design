import os
from openai import OpenAI
from .prompts.prompt import generate_final_summary
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv("GOOGLE_API_KEY")
client = OpenAI(
    api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def combine_chunk_summaries(
    text: str, summary_type: str, text_was_splitted: bool
) -> str:
    """Creates a final summary from text or combined summaries using Gemini API.

    Available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        text (str): The text or combined summaries to process.
        summary_type (str): The type of summary to generate.
        text_was_splitted (bool): Whether the original text was split into chunks.

    Returns:
        str: The final summary, not just a prompt
    """
    # Get the appropriate prompt for this summary type and situation
    prompt = generate_final_summary(summary_type, text_was_splitted)

    # Create the full prompt with the input text
    full_prompt = f"""
    {prompt}
    
    {'' if text_was_splitted else '--- TEXT TO SUMMARIZE ---'}
    {text}
    {'' if text_was_splitted else '--- TEXT TO SUMMARIZE ---'}
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
