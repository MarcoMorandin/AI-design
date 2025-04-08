# app/services/llm.py
import logging
from typing import Optional

from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the Gemini client
try:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    logger.info(f"Initialized Gemini client with model: {settings.GEMINI_MODEL}")
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {str(e)}")
    client = None

async def generate_content(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Generate content using the Gemini API.
    
    Args:
        prompt: The prompt to send to the model.
        system_prompt: Optional system prompt to guide the model's behavior.
        
    Returns:
        The generated text response.
        
    Raises:
        Exception: If the API call fails.
    """
    try:
        if not client:
            raise Exception("Gemini client not initialized. Check API key configuration.")
            
        if system_prompt:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt
                )
            )
        else:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error generating content with Gemini: {str(e)}")
        raise Exception(f"Failed to generate content: {str(e)}")