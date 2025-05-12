import os
from openai import OpenAI
from .prompts.prompt import fix_formulas_prompt
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv("GOOGLE_API_KEY")
client = OpenAI(
    api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def fix_latex_formulas(text: str) -> str:
    """Fixes formulas in text to use proper LaTeX format using Gemini API.

    Args:
        text (str): The text containing formulas to format correctly.

    Returns:
        str: Text with properly formatted LaTeX formulas
    """
    # Get the prompt for formula correction
    prompt = fix_formulas_prompt()

    # Create the full prompt with the input text
    full_prompt = f"""
    {prompt}
    
    --- TEXT WITH FORMULAS ---
    {text}
    --- TEXT WITH FORMULAS ---
    """

    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a math syntax expert."},
            {"role": "user", "content": full_prompt},
        ],
    )

    # Return the actual text with properly formatted formulas, not just the prompt
    return response.choices[0].message.content