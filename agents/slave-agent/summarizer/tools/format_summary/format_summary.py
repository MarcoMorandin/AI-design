from typing import Dict, Any, List
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
from utils import sanitize_content, validate_json_serializable

load_dotenv()
logger = logging.getLogger(__name__)

# Get API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
MODEL = os.getenv("MODEL", "gemini-2.0-flash")


async def format_summary(
    summaries: List[str], style: str = "standard", title: str = ""
) -> Dict[str, Any]:
    """
    Combines and formats multiple chunk summaries into a cohesive final summary.

    Args:
        summaries: List of summaries to combine
        style: The desired style of the final summary
        title: Optional title or context for the summary

    Returns:
        Dict containing the formatted, combined summary

    Tool:
        name: format_summary
        description: Combines and formats multiple chunk summaries into a cohesive final summary
        input_schema:
            type: object
            properties:
                summaries:
                    type: array
                    description: List of summaries to combine
                    items:
                        type: string
                style:
                    type: string
                    description: The style of the final summary (technical, bullet-points, standard, concise, detailed)
                    enum: [technical, bullet-points, standard, concise, detailed]
                    default: standard
                title:
                    type: string
                    description: Optional title or context for the summary
                    default: ""
            required:
                - summaries
        output_schema:
            type: object
            properties:
                combined_summary:
                    type: string
                    description: The formatted, combined summary
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message or error information
    """
    try:
        logger.info(
            f"Formatting and combining {len(summaries)} summaries in {style} style"
        )

        # Validate input summaries
        if not summaries or len(summaries) == 0:
            logger.warning("No summaries provided to format_summary")
            return {
                "success": False,
                "combined_summary": "",
                "message": "No summaries provided to combine",
            }

        # Filter out empty or None summaries and sanitize them
        valid_summaries = []
        for s in summaries:
            if s and s.strip():
                # Sanitize each summary
                sanitized = sanitize_content(str(s))
                if sanitized and sanitized.strip():
                    valid_summaries.append(sanitized)
        
        if not valid_summaries:
            logger.warning("All provided summaries are empty or corrupted after sanitization")
            return {
                "success": False,
                "combined_summary": "",
                "message": "All provided summaries are empty or corrupted",
            }

        logger.info(f"Valid summaries after filtering: {len(valid_summaries)}")

        # If there's only one summary and it's not too long, return it directly
        if len(valid_summaries) == 1 and len(valid_summaries[0]) < 4000:
            return {
                "success": True,
                "combined_summary": valid_summaries[0],
                "message": "Single summary returned without need for combination",
            }

        # Initialize the OpenAI client with Gemini base URL and API key
        client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=OPENAI_BASE_URL)

        # Create style-specific formatting instructions
        style_instructions = {
            "technical": "Format the summary in an academic style, preserving all technical terms, mathematical formulas (using LaTeX where appropriate), and maintaining precision. Structure with appropriate sections and subsections.",
            "bullet-points": "Format the summary as a hierarchical bullet-point list, organizing information logically. Group related points together under clear headings. Use concise language for each point.",
            "standard": "Format the summary as a cohesive narrative with clear paragraphs, transitions between topics, and a logical flow. Ensure it reads as a single, unified document rather than disconnected sections.",
            "concise": "Format the summary to be extremely brief while capturing essential information. Use tight, economical language. Aim for a significantly reduced length while maintaining core meaning.",
            "detailed": "Format the summary to include both main points and supporting details in a structured document. Include examples where relevant. Create a comprehensive overview that could substitute for the original content.",
        }

        # Get style instructions or default to standard
        format_instruction = style_instructions.get(
            style, style_instructions["standard"]
        )

        # Combine summaries into a single text for processing
        combined_text = "\n\n".join(
            [f"Summary Part {i+1}:\n{summary}" for i, summary in enumerate(valid_summaries)]
        )
        
        # Validate that the combined text is not too corrupted
        combined_text = sanitize_content(combined_text)
        if not combined_text or len(combined_text.strip()) < 20:
            logger.error("Combined text is too short or corrupted after sanitization")
            # Use direct fallback
            if style == "bullet-points":
                combined_summary = "# Combined Summary\n\n" + "\n\n".join([
                    f"## Section {i+1}\n{summary.strip()}" 
                    for i, summary in enumerate(valid_summaries)
                ])
            else:
                combined_summary = "# Combined Summary\n\n" + "\n\n".join([
                    f"**Section {i+1}:** {summary.strip()}" 
                    for i, summary in enumerate(valid_summaries)
                ])
            
            return {
                "success": True,
                "combined_summary": combined_summary,
                "message": "Used fallback formatting due to corrupted input data",
            }

        # Create the formatting prompt
        title_context = f"Title/Context: {title}\n\n" if title else ""

        formatting_prompt = f"""
        {title_context}I have multiple summaries of different sections of a document that need to be combined into a single cohesive summary:

        {combined_text}

        Please integrate these summaries into a single, well-organized summary that flows naturally.

        {format_instruction}

        Remove repetition, resolve contradictions, and ensure the final summary is coherent and unified.
        """

        # Call the LLM to generate the formatted summary
        async def make_api_call():
            return await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert editor specializing in combining and formatting summaries into cohesive documents.",
                    },
                    {"role": "user", "content": formatting_prompt},
                ],
                temperature=0.3,  # Lower temperature for consistent formatting
                max_tokens=2000,
            )

        try:
            # Use retry_api_call to handle transient API errors
            response = await retry_api_call(
                make_api_call, max_retries=3, initial_delay=1.0, backoff_factor=2.0
            )

            if not response or not response.choices or not response.choices[0].message:
                logger.error("API returned empty or invalid response")
                return {
                    "success": False,
                    "combined_summary": "",
                    "message": "API returned an invalid response. Please try again.",
                }

            combined_summary = response.choices[0].message.content
            
            # Check if the content is None or empty
            if combined_summary is None:
                logger.error("API returned None content, falling back to simple combination")
                # Improved fallback: create a properly formatted combined summary
                if style == "bullet-points":
                    combined_summary = "# Combined Summary\n\n" + "\n\n".join([
                        f"## Section {i+1}\n{summary.strip()}" 
                        for i, summary in enumerate(valid_summaries)
                    ])
                else:
                    combined_summary = "# Combined Summary\n\n" + "\n\n".join([
                        f"**Section {i+1}:** {summary.strip()}" 
                        for i, summary in enumerate(valid_summaries)
                    ])
                
                # Sanitize the fallback content
                combined_summary = sanitize_content(combined_summary)
                
                if not combined_summary or len(combined_summary.strip()) < 10:
                    return {
                        "success": False,
                        "combined_summary": "",
                        "message": "API returned None content and fallback failed. Please try again.",
                    }
            
            # Sanitize the content to remove any invalid control characters
            combined_summary = sanitize_content(combined_summary)
            
            if not combined_summary or not combined_summary.strip():
                logger.error("API returned content that became empty after sanitization")
                # Try the improved fallback approach
                if style == "bullet-points":
                    combined_summary = "# Combined Summary\n\n" + "\n\n".join([
                        f"## Section {i+1}\n{summary.strip()}" 
                        for i, summary in enumerate(valid_summaries)
                    ])
                else:
                    combined_summary = "# Combined Summary\n\n" + "\n\n".join([
                        f"**Section {i+1}:** {summary.strip()}" 
                        for i, summary in enumerate(valid_summaries)
                    ])
                
                # Sanitize the fallback content
                combined_summary = sanitize_content(combined_summary)
                
                if not combined_summary or not combined_summary.strip():
                    return {
                        "success": False,
                        "combined_summary": "",
                        "message": "Content became empty after sanitization and fallback failed. Please try again.",
                    }
            
            # Validate that the content is JSON serializable
            if not validate_json_serializable(combined_summary):
                logger.error("API returned content that is not JSON serializable")
                combined_summary = sanitize_content(combined_summary)  # Try to fix it again
                if not validate_json_serializable(combined_summary):
                    return {
                        "success": False,
                        "combined_summary": "",
                        "message": "API returned content with invalid characters that cannot be serialized.",
                    }
            
            logger.info(f"Successfully combined and formatted summaries. Length: {len(combined_summary)}")

            return {
                "success": True,
                "combined_summary": combined_summary,
                "message": "Successfully combined and formatted summaries",
            }

        except Exception as e:
            logger.error(f"Error in API call after retries: {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "combined_summary": "",
                "message": f"Error formatting and combining summaries: {str(e)}",
            }

    except Exception as e:
        logger.error(f"Error formatting and combining summaries: {str(e)}")
        return {
            "success": False,
            "combined_summary": "",
            "message": f"Error formatting and combining summaries: {str(e)}",
        }
