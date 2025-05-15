from typing import Dict, Any, List
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


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
        logger.info(
            f"Generating folder structure for {len(analyzed_documents)} documents"
        )

        # Create a clean list of properly formatted documents
        cleaned_documents = []
        
        # First, preprocess the analyzed_documents to ensure they're all properly formatted
        if isinstance(analyzed_documents, str):
            # If the whole analyzed_documents is a string, try to parse it
            try:
                analyzed_documents = json.loads(analyzed_documents)
                logger.info("Converted entire analyzed_documents from string to list/dict")
            except json.JSONDecodeError:
                logger.error("Invalid analyzed_documents format, couldn't parse JSON")
                analyzed_documents = []
        
        # Now process each document
        for i, doc in enumerate(analyzed_documents):
            try:
                # Skip if it's not the right type
                if not isinstance(doc, dict):
                    if isinstance(doc, str):
                        try:
                            parsed_doc = json.loads(doc)
                            if isinstance(parsed_doc, dict) and "file_id" in parsed_doc:
                                cleaned_documents.append(parsed_doc)
                                continue
                            else:
                                logger.warning(f"Document index {i} parsed as JSON but lacks required fields")
                        except json.JSONDecodeError:
                            pass
                    logger.warning(f"Skipping document at index {i} with type {type(doc)}")
                    continue
                
                # If it's a dict, make sure it has the required fields
                if "file_id" in doc:
                    cleaned_documents.append(doc)
                else:
                    logger.warning(f"Document at index {i} is missing file_id field")
            except Exception as e:
                logger.warning(f"Error processing document at index {i}: {str(e)}")
                continue
        
        logger.info(f"Successfully processed {len(cleaned_documents)} valid documents out of {len(analyzed_documents)}")
        
        # Group files by document type (if available from analysis)
        type_groups = defaultdict(list)

        # Map current files to their analysis
        file_map = {}
        for doc in cleaned_documents:
            file_id = doc.get("file_id", "")
            if file_id:
                file_map[file_id] = doc

                # Group by document type
                doc_type = doc.get("document_type", "unknown")
                type_groups[doc_type].append(
                    {
                        "file_id": file_id,
                        "file_name": doc.get("file_name", "Unknown"),
                        "topics": doc.get("topics", []),
                    }
                )

        # Create proposed folder structure
        proposed_structure = {"root": {"name": "Course Materials", "subfolders": []}}

        # Common course folder categories
        common_folders = [
            {"name": "Lectures", "types": ["lecture"], "match_priority": 1},
            {
                "name": "Assignments",
                "types": ["assignment", "homework"],
                "match_priority": 1,
            },
            {
                "name": "Assessments",
                "types": ["exam", "test", "quiz", "assessment"],
                "match_priority": 1,
            },
            {
                "name": "Course Information",
                "types": ["course_info", "syllabus"],
                "match_priority": 2,
            },
            {
                "name": "Reference Materials",
                "types": ["reference_material", "resource"],
                "match_priority": 2,
            },
            {"name": "Additional Resources", "types": ["unknown"], "match_priority": 3},
        ]

        # Add folders and assign files
        file_assignments = {}
        for folder in common_folders:
            folder_files = []

            # Add files that match this folder's document types
            for doc_type in folder["types"]:
                if doc_type in type_groups:
                    folder_files.extend(type_groups[doc_type])

            # Only create the folder if it has files
            if folder_files:
                folder_id = f"new_folder_{folder['name'].lower().replace(' ', '_')}"
                proposed_structure["root"]["subfolders"].append(
                    {
                        "id": folder_id,
                        "name": folder["name"],
                        "files": folder_files,
                        "priority": folder["match_priority"],
                    }
                )

                # Record file assignments
                for file in folder_files:
                    file_assignments[file["file_id"]] = folder_id

        # Find any files that weren't assigned and add to "Additional Resources"
        unassigned_files = []
        
        # Process folder_structure to handle potential string format
        processed_folder_structure = folder_structure
        if isinstance(folder_structure, str):
            try:
                processed_folder_structure = json.loads(folder_structure)
                logger.info("Converted folder_structure from string to list/dict")
            except json.JSONDecodeError:
                logger.error("Invalid folder_structure format, couldn't parse JSON")
                processed_folder_structure = []
        
        # Ensure each item in folder_structure is a dictionary before accessing
        for item in processed_folder_structure:
            try:
                if not isinstance(item, dict):
                    logger.warning(f"Skipping folder item of type {type(item)}")
                    continue
                    
                if "type" not in item or "id" not in item:
                    logger.warning("Skipping folder item missing required fields")
                    continue
                
                if item["type"] == "file" and item["id"] not in file_assignments:
                    unassigned_files.append(
                        {"file_id": item["id"], "file_name": item.get("name", "Unknown File")}
                    )
            except Exception as e:
                logger.warning(f"Error processing folder item: {str(e)}")
                continue

        # Add Additional Resources folder if needed
        if unassigned_files and not any(
            f["name"] == "Additional Resources"
            for f in proposed_structure["root"]["subfolders"]
        ):
            folder_id = "new_folder_additional_resources"
            proposed_structure["root"]["subfolders"].append(
                {
                    "id": folder_id,
                    "name": "Additional Resources",
                    "files": unassigned_files,
                    "priority": 3,
                }
            )

            # Record file assignments
            for file in unassigned_files:
                file_assignments[file["file_id"]] = folder_id

        # Generate explanation
        explanation = f"""
        I've analyzed {len(analyzed_documents)} documents and organized them into {len(proposed_structure['root']['subfolders'])} logical sections:
        
        {', '.join(f['name'] for f in proposed_structure['root']['subfolders'])}
        
        This organization follows standard course structure conventions, grouping related materials together for easier navigation.
        Documents were categorized based on their content and filename patterns.
        """

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
