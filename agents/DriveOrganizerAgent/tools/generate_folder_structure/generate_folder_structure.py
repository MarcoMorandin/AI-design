from typing import Dict, Any, List
import logging
from collections import defaultdict
import json
import re
from itertools import chain
import os
from openai import OpenAI
import uuid
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FOLDER_STRUCTURE_PROMPT = """
You are an expert at organizing university course materials. I'll provide you with analyzed documents containing summaries, topics, and document types.

Your task: Create a folder structure that organizes these materials optimally for a university student.

Guidelines:
- Create folders based on both document types (lectures, assignments) AND common topics
- Maximum one level of subfolder depth under the root folder
- Group related materials together (e.g., assignments on same topic, lecture series)
- Use clear, descriptive folder names
- Every file must be assigned to a folder

Return a JSON object with this structure:
```json
{
    "folders": [
        {
            "name": "Folder Name",
            "description": "Short explanation of what's in this folder",
            "files": [
                {"file_id": "id1", "file_name": "name1"}
            ]
        }
    ],
    "explanation": "Overall explanation of your organizational approach"
}
""".strip()


async def call_llm_for_folder_structure(
    analyzed_documents: List[Dict[str, Any]],
) -> Dict:
    """Call an LLM to generate an intelligent folder structure."""
    try:
        # Initialize the OpenAI client (ensure OPENAI_API_KEY is set in environment)
        client = OpenAI(
            api_key=os.environ.get("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        # Prepare the input data
        processed_docs = []
        for doc in analyzed_documents:
            if not isinstance(doc, dict):
                continue

            # Add file_id if missing
            if "file_id" not in doc:
                doc["file_id"] = str(uuid.uuid4())

            # Add file_name if missing
            if "file_name" not in doc:
                doc_type = doc.get("document_type", "unknown")
                topics = doc.get("topics", [])
                topic_text = topics[0] if topics else "untitled"
                doc["file_name"] = f"{doc_type}_{topic_text}.pdf"

            processed_docs.append(
                {
                    "file_id": doc["file_id"],
                    "file_name": doc["file_name"],
                    "document_type": doc.get("document_type", "unknown"),
                    "topics": doc.get("topics", []),
                    "summary": doc.get("summary", ""),
                }
            )

        # Call the LLM
        response = client.chat.completions.create(
            model="gemini-2.0-flash",  # Use appropriate model
            messages=[
                {"role": "system", "content": FOLDER_STRUCTURE_PROMPT},
                {"role": "user", "content": json.dumps(processed_docs)},
            ],
            response_format={"type": "json_object"},
        )

        # Parse and return the response
        llm_response = json.loads(response.choices[0].message.content)
        return {"success": True, "result": llm_response}
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def generate_folder_structure(
    analyzed_documents: List[Dict[str, Any]], folder_structure: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generates an optimized folder structure based on document analysis.
    Takes the analyzed document data and current folder structure, and proposes a new organization.

    Args:
        analyzed_documents: Array of analyzed document data
        folder_structure: The current folder structure

    Returns:
        Dict containing proposed structure, explanation and success status

    Tool:
        name: generate_folder_structure
        description: Generates an optimized folder structure based on document analysis
        input_schema:
            type: object
            properties:
                analyzed_documents:
                    type: array
                    description: Array of analyzed document data
                folder_structure:
                    type: array
                    description: The current folder structure
            required:
                - analyzed_documents
                - folder_structure
        output_schema:
            type: object
            properties:
                proposed_structure:
                    type: object
                    description: Proposed folder structure with file assignments
                explanation:
                    type: string
                    description: Explanation of the organizational approach
                success:
                    type: boolean
                    description: Whether the operation was successful
    """
    try:

        # Parse analyzed_documents if it's a string
        if isinstance(analyzed_documents, str):
            try:
                analyzed_documents = json.loads(analyzed_documents)
                logger.info("Converted analyzed_documents from string to list/dict")
            except json.JSONDecodeError:
                logger.error("Invalid analyzed_documents format, couldn't parse JSON")
                return {
                    "success": False,
                    "proposed_structure": {},
                    "explanation": "Could not parse analyzed documents.",
                }

        logger.info(
            f"Generating folder structure for {len(analyzed_documents)} documents"
        )

        # Parse folder_structure if it's a string
        processed_folder_structure = folder_structure
        if isinstance(folder_structure, str):
            try:
                processed_folder_structure = json.loads(folder_structure)
            except json.JSONDecodeError:
                logger.error("Invalid folder_structure format, couldn't parse JSON")
                processed_folder_structure = []

        # Map existing files from folder structure by ID
        folder_items_by_id = {}
        for item in processed_folder_structure:
            if isinstance(item, dict) and "id" in item:
                folder_items_by_id[item["id"]] = item

        # Add file_name to documents if missing but present in folder structure
        for doc in analyzed_documents:
            if isinstance(doc, dict) and "file_id" in doc and "file_name" not in doc:
                file_id = doc["file_id"]
                if file_id in folder_items_by_id:
                    doc["file_name"] = folder_items_by_id[file_id].get(
                        "name", "Unknown File"
                    )

        # Call LLM to generate folder structure
        llm_result = await call_llm_for_folder_structure(analyzed_documents)

        if not llm_result["success"]:
            logger.error(f"LLM call failed: {llm_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "proposed_structure": {},
                "explanation": f"Failed to generate folder structure: {llm_result.get('error', 'Unknown error')}",
            }

        # Format the result into the expected structure
        llm_folders = llm_result["result"]["folders"]
        explanation = llm_result["result"]["explanation"]

        # Convert to the expected format
        proposed_structure = {"root": {"name": "Course Materials", "subfolders": []}}

        for idx, folder in enumerate(llm_folders):
            folder_id = f"new_folder_{idx}_{folder['name'].lower().replace(' ', '_')}"
            folder_files = [
                {
                    "file_id": file["file_id"],
                    "file_name": file["file_name"],
                    "topics": [],  # We could add topics here if needed
                }
                for file in folder["files"]
            ]

            proposed_structure["root"]["subfolders"].append(
                {
                    "id": folder_id,
                    "name": folder["name"],
                    "description": folder.get("description", ""),
                    "files": folder_files,
                    "priority": 1,  # All folders have equal priority in this implementation
                }
            )

        logger.info(
            f"Successfully generated folder structure with {len(proposed_structure['root']['subfolders'])} folders"
        )

        return {
            "success": True,
            "proposed_structure": proposed_structure,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Error generating folder structure: {str(e)}", exc_info=True)
        return {
            "success": False,
            "proposed_structure": {},
            "explanation": f"Error generating folder structure: {str(e)}",
        }
