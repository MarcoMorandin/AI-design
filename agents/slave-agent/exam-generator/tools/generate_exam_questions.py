from typing import Dict, Any
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


async def generate_exam_questions(
    document_content: str, exam_structure: Dict[str, Any], include_answers: bool = True
) -> Dict[str, Any]:
    """
    Generates exam questions based on document content and the exam structure.

    Args:
        document_content: The text content of the document
        exam_structure: The previously generated exam structure
        include_answers: Whether to include answers/solutions

    Returns:
        Dict containing the complete exam with questions and answers

    Tool:
        name: generate_exam_questions
        description: Creates exam questions based on document content and exam structure
    """
    try:
        if not document_content:
            return {
                "success": False,
                "message": "No document content provided",
                "exam": None,
            }

        if not exam_structure:
            return {
                "success": False,
                "message": "No exam structure provided",
                "exam": None,
            }

        # Convert exam_structure to dictionary if it's a string (JSON)
        if isinstance(exam_structure, str):
            try:
                exam_structure = json.loads(exam_structure)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Provided exam structure is not valid JSON",
                    "exam": None,
                }

        # Initialize OpenAI client with API key and base URL
        client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

        # Check if we need to access the exam_structure directly or through its 'exam_structure' property
        if "exam_structure" in exam_structure and isinstance(
            exam_structure["exam_structure"], dict
        ):
            structure = exam_structure["exam_structure"]
        else:
            structure = exam_structure

        # Safely extract data from nested structure
        exam_title = structure.get("exam_title", "Academic Exam")
        topics = structure.get("topics", [])
        estimated_duration = structure.get("estimated_duration_minutes", 60)

        # Create a prompt for the model
        prompt = f"""
        Create an exam based on the provided educational content and structure.
        
        Exam Title: {exam_title}
        Topics: {json.dumps(topics)}
        
        Your task:
        1. Generate questions for each topic according to the specified question types and counts
        2. For multiple choice questions, generate 4-5 options with one correct answer
        3. For short answer or essay questions, provide guidelines for expected answers
        4. For each question, {"provide the correct answer" if include_answers else "do NOT include answers"}
        
        Return a valid JSON object with the following structure:
        {{
            "exam_title": "{exam_title}",
            "questions": [
                {{
                    "question_number": 1,
                    "topic": "Topic name",
                    "question_type": "multiple_choice|short_answer|essay|etc",
                    "question_text": "The question itself",
                    "options": ["Option A", "Option B", ...] (for multiple choice only),
                    "answer": "Correct answer or solution" (only if include_answers is true),
                    "points": Number of points for this question
                }},
                // more questions
            ],
            "total_points": Sum of all question points,
            "duration_minutes": {estimated_duration}
        }}
        
        Here is the document content (truncated if necessary):
        {document_content[:15000] if len(document_content) > 15000 else document_content}
        """

        # Call the model
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an educational assessment specialist who creates high-quality exam questions based on provided content.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        # Extract and parse the response
        questions_text = response.choices[0].message.content
        questions = json.loads(questions_text)

        return {
            "success": True,
            "message": "Exam questions generated successfully",
            "exam": questions,
        }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse model response: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg, "exam": None}

    except Exception as e:
        error_msg = f"Error generating exam questions: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg, "exam": None}
