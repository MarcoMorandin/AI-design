from typing import Dict, Any
import logging
import os
import sys
import traceback
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Add the parent directory to the path to import api_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api_utils import retry_api_call

# Import utils for content sanitization
sys.path.append(os.path.dirname(__file__) + "/..")
from utils import sanitize_content

load_dotenv()
logger = logging.getLogger(__name__)

# Get API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
MODEL = os.getenv("MODEL", "gemini-2.0-flash")


async def summarize_chunk(content: str, style: str = "standard") -> Dict[str, Any]:
    """
    Summarizes a chunk of markdown content in the specified style.

    Args:
        content: The markdown content to be summarized
        style: The style of the summary (technical, bullet-pointed, standard, concise, detailed)

    Returns:
        Dict containing the summary in the requested style

    Tool:
        name: summarize_chunk
        description: Summarizes a chunk of markdown content in the specified style
        input_schema:
            type: object
            properties:
                content:
                    type: string
                    description: The markdown content to be summarized
                style:
                    type: string
                    description: The style of the summary (technical, bullet-points, standard, concise, detailed)
                    enum: [technical, bullet-points, standard, concise, detailed]
                    default: standard
            required:
                - content
        output_schema:
            type: object
            properties:
                summary:
                    type: string
                    description: The generated summary
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message or error information
    """
    try:
        logger.info(f"Summarizing content chunk in {style} style")

        # Validate input content
        if not content or not content.strip():
            logger.warning("Empty or None content provided to summarize_chunk")
            return {
                "success": False,
                "summary": "",
                "message": "No content provided to summarize",
            }

        # Sanitize content to remove invalid control characters
        content = sanitize_content(content)
        
        if not content:
            logger.warning("Content is empty after sanitization")
            return {
                "success": False,
                "summary": "",
                "message": "Content is empty after removing invalid characters",
            }

        # Initialize the OpenAI client with Gemini base URL and API key
        client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=OPENAI_BASE_URL)

        # Create a style-specific prompt
        style_instructions = {
            "technical": "Create a technical summary that preserves mathematical formulas, technical terms, and maintains academic precision. Use LaTeX formatting for equations where appropriate.",
            "bullet-points": "Create a bullet-point summary highlighting the key points and important information. Use clear, concise language and organize points hierarchically.",
            "standard": "Create a comprehensive summary in paragraph form that captures the main ideas and important details in a well-structured, flowing narrative.",
            "concise": "Create an extremely concise summary focusing only on the most essential information. Aim for brevity while maintaining clarity.",
            "detailed": "Create a detailed summary that captures main points as well as supporting details, examples, and nuances from the original text.",
        }

        # Get the style-specific instructions or default to standard if style is not recognized
        style_instruction = style_instructions.get(
            style, style_instructions["standard"]
        )

        # Create prompt for summarization
        summarization_prompt = f"""
        Summarize the following markdown content:

        {content}

        {style_instruction}

        Maintain the markdown formatting where appropriate. Ensure the summary remains faithful to the original content.
        """

        # Call the LLM to generate the summary
        async def make_api_call():
            return await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert summarizer that creates high-quality summaries of markdown text.",
                    },
                    {"role": "user", "content": summarization_prompt},
                ],
                temperature=0.3,  # Lower temperature for more focused summaries
                max_tokens=300,   # Moderate length for individual chunk summaries
            )

        try:
            # Use retry_api_call to handle transient API errors with longer delays for rate limiting
            response = await retry_api_call(
                make_api_call, max_retries=5, initial_delay=2.0, backoff_factor=2.0
            )

            if not response or not response.choices or not response.choices[0].message:
                logger.error("API returned empty or invalid response")
                return {
                    "success": False,
                    "summary": "",
                    "message": "API returned an invalid response. Please try again.",
                }

            summary = response.choices[0].message.content
            
            # Check if the content is None or empty
            if summary is None:
                logger.error("API returned None content for chunk summary")
                return {
                    "success": False,
                    "summary": "",
                    "message": "API returned None content. Please try again.",
                }
            
            # Sanitize the summary content
            summary = sanitize_content(summary)
            
            if not summary or not summary.strip():
                logger.error("Summary is empty after sanitization")
                return {
                    "success": False,
                    "summary": "",
                    "message": "Summary is empty after sanitization. Please try again.",
                }
            
            logger.info(f"Successfully generated {style} summary")

            return {
                "success": True,
                "summary": summary,
                "message": f"Successfully generated {style} summary",
            }

        except Exception as e:
            logger.error(f"Error in API call after retries: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "summary": "",
                "message": f"Error in API call after retries: {str(e)}",
            }

    except Exception as e:
        logger.error(f"Error summarizing content: {str(e)}")
        return {
            "success": False,
            "summary": "",
            "message": f"Error summarizing content: {str(e)}",
        }
