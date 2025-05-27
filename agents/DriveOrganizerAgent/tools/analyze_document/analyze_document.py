from typing import Dict, Any
import logging
import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Get API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)


async def analyze_document(
    content: str, file_name: str, mime_type: str = "", file_id: str = ""
) -> Dict[str, Any]:
    """
    Analyzes the content of a document to:
    1. Create a brief summary
    2. Extract key topics
    3. Categorize the document type

    This function provides input for organizing files into logical course sections.

    Args:
        content: The text content of the document
        file_name: The name of the file
        mime_type: The MIME type of the file
        file_id: The Google Drive file ID

    Returns:
        Dict containing document analysis results

    Tool:
        name: analyze_document
        description: Analyzes document content to extract key topics and create a summary
        input_schema:
            type: object
            properties:
                content:
                    type: string
                    description: The text content of the document
                file_name:
                    type: string
                    description: The name of the file
                mime_type:
                    type: string
                    description: The MIME type of the file
                file_id:
                    type: string
                    description: The Google Drive file ID
            required:
                - content
                - file_name
                - file_id
        output_schema:
            type: object
            properties:
                summary:
                    type: string
                    description: A brief summary of the document content
                topics:
                    type: array
                    description: List of topics/categories extracted from the document
                document_type:
                    type: string
                    description: The type of document (e.g., lecture, assignment, reference material)
                success:
                    type: boolean
                    description: Whether the operation was successful
                file_id:
                    type: string
                    description: The Google Drive file ID
    """
    try:
        logger.info(f"Analyzing document: {file_name}")

        # Check if content is too short for meaningful analysis
        if len(content.strip()) < 50:
            return {
                "success": True,
                "summary": f"File appears to have minimal text content: {file_name}",
                "topics": ["unknown"],
                "document_type": "unknown",
            }

        # Initialize the OpenAI client with Gemini base URL and API key
        client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=OPENAI_BASE_URL)

        # Create a prompt for document analysis
        analysis_prompt = f"""
        Analyze the following document content from a university course file named "{file_name}".
        
        Document content: 
        {content}

        Provide your analysis as a JSON object with the following fields:
        1. "summary": A concise summary of the document (max 100 words)
        2. "topics": An array of 2-5 key topics covered in the document
        3. "document_type": The most likely document type from these options: 
           - lecture
           - assignment
           - assessment
           - course_info
           - reference_material
           - unknown
        
        Base your analysis on both the document content and filename patterns.
        Return ONLY valid JSON.
        """

        # Call Gemini via OpenAI SDK interface
        response = await client.chat.completions.create(
            model="gemini-2.0-flash",  # Or whatever Gemini model is available
            messages=[
                {
                    "role": "system",
                    "content": "You are a document analysis assistant that returns structured JSON only.",
                },
                {"role": "user", "content": analysis_prompt},
            ],
            response_format={"type": "json_object"},
        )

        # Extract and parse the response
        analysis_text = response.choices[0].message.content
        analysis = json.loads(analysis_text)

        # Extract the required fields, with fallbacks in case any are missing
        summary = analysis.get("summary", f"Analysis of {file_name}")
        topics = analysis.get("topics", ["course_topic"])
        document_type = analysis.get("document_type", "unknown")

        logger.info(
            f"Successfully analyzed document: {file_name}, type: {document_type}"
        )

        return {
            "success": True,
            "summary": summary,
            "topics": topics,
            "document_type": document_type,
            "file_id": file_id,
        }

    except json.JSONDecodeError as je:
        logger.error(f"Error parsing Gemini response: {str(je)}", exc_info=True)
        # Fall back to basic analysis

    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}", exc_info=True)
        return {
            "success": False,
            "summary": "",
            "topics": [],
            "document_type": "unknown",
        }
