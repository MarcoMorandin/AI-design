from typing import Dict, Any, List
import logging
import os
import json
from dotenv import load_dotenv
import openai
import datetime

load_dotenv()
logger = logging.getLogger(__name__)

# Get API configuration from environment
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-2.0-flash")
BASE_URL = os.getenv(
    "BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)


async def format_exam(
    exam: Dict[str, Any],
    format_type: str = "markdown",
    include_answers: bool = True,
) -> Dict[str, Any]:
    """
    Formats the exam into a presentable document.

    Args:
        exam: The complete exam with questions and answers
        format_type: The format to generate (markdown, plain_text)
        include_answers: Whether to include an answer key

    Returns:
        Dict containing the formatted exam document

    Tool:
        name: format_exam
        description: Formats the exam into a presentable document
    """
    try:
        if not exam:
            return {
                "success": False,
                "message": "No exam data provided",
                "formatted_exam": None,
            }

        # Initialize OpenAI client with API key and base URL
        client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

        # Create a prompt for the model
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        prompt = f"""
        Format the following exam into a professional {format_type} document.

        Today's Date: {current_date}
        Format Type: {format_type}
        Include Answer Key: {"Yes" if include_answers else "No"}
        
        Your task:
        1. Create a well-structured {format_type} document that presents the exam professionally
        2. Include proper title, instructions, and section headings
        3. Format all questions according to their type (multiple choice, short answer, etc.)
        4. {"Include an answer key section at the end" if include_answers else "Do NOT include any answers"}
        5. For multiple choice questions, use proper formatting for options (A, B, C, D or 1, 2, 3, 4)
        6. Add page numbers and proper spacing
        
        Here is the exam content to format:
        {json.dumps(exam)}
        """

        # Call the model
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"You are an educational document formatter who creates professional {format_type} exam documents.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        # Extract the formatted document
        formatted_exam = response.choices[0].message.content

        # Create the answer key as a separate document if requested
        answer_key = None
        if include_answers:
            answer_key_prompt = f"""
            Create an answer key document for the following exam in {format_type} format.
            
            Your task:
            1. List all questions with their correct answers
            2. For multiple choice questions, include the letter/number of the correct option
            3. For short answer questions, provide the key points that should be included
            4. For essay questions, provide the evaluation criteria
            
            Here is the exam content:
            {json.dumps(exam)}
            """

            answer_key_response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an educational assessment specialist who creates clear answer keys.",
                    },
                    {"role": "user", "content": answer_key_prompt},
                ],
            )

            answer_key = answer_key_response.choices[0].message.content

        return {
            "success": True,
            "message": "Exam formatted successfully",
            "formatted_exam": formatted_exam,
            "answer_key": answer_key if include_answers else None,
            "format_type": format_type,
        }

    except Exception as e:
        error_msg = f"Error formatting exam: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg, "formatted_exam": None}
