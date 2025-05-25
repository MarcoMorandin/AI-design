from typing import Dict, Any, List
import logging
import os
import json
from dotenv import load_dotenv
import openai

load_dotenv()
logger = logging.getLogger(__name__)

# Get API configuration from environment
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-2.0-flash")
BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)


async def generate_exam_structure(
    document_content: str,
    file_name: str,
    exam_type: str = "quiz",
    difficulty_level: str = "moderate",
    num_questions: int = 10,
) -> Dict[str, Any]:
    """
    Analyzes content and generates an exam structure with question types and topics.

    Args:
        document_content: The text content of the document
        file_name: The name of the original file
        exam_type: The type of exam to generate (quiz, test, final)
        difficulty_level: The difficulty level (easy, moderate, difficult)
        num_questions: The number of questions to include

    Returns:
        Dict containing the exam structure with topics and question types

    Tool:
        name: generate_exam_structure
        description: Creates an exam structure with topics and question types based on document content
    """
    try:
        if not document_content:
            return {
                "success": False,
                "message": "No document content provided",
                "exam_structure": None,
            }

        # Initialize OpenAI client with API key and base URL
        client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

        # Create a prompt for the model
        prompt = f"""
        Analyze the following educational content and create a structured exam plan.
        
        Document Name: {file_name}
        Exam Type: {exam_type}
        Difficulty Level: {difficulty_level}
        Number of Questions: {num_questions}
        
        Your task:
        1. Identify {min(5, num_questions)} key topics from the content
        2. For each topic, suggest specific question types (multiple choice, short answer, essay, etc.)
        3. Distribute the {num_questions} questions across the topics
        4. For each topic, suggest specific concepts to test
        
        Return a valid JSON object with the following structure:
        {{
            "exam_title": "Generated title based on content",
            "topics": [
                {{
                    "topic_name": "Topic 1",
                    "question_count": X,
                    "question_types": ["multiple_choice", "short_answer"],
                    "concepts": ["concept 1", "concept 2"]
                }},
                // more topics
            ],
            "total_questions": {num_questions},
            "estimated_duration_minutes": Estimated time to complete
        }}
        
        Here is the document content (truncated if necessary):
        {document_content[:10000] if len(document_content) > 10000 else document_content}
        """

        # Call the model
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an educational assessment specialist who creates well-structured exams based on provided content.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        # Extract and parse the response
        structure_text = response.choices[0].message.content
        structure = json.loads(structure_text)

        return {
            "success": True,
            "message": "Exam structure generated successfully",
            "exam_structure": structure,
        }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse model response: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg, "exam_structure": None}

    except Exception as e:
        error_msg = f"Error generating exam structure: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg, "exam_structure": None}
