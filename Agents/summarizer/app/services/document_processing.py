# app/services/document_processing.py
import logging
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple, Optional

from app.utils.file_handler import extract_from_pdf, extract_from_word, extract_from_text
from app.utils.prompts import SYSTEM_PROMPT, PROCESS_CHUNK_PROMPT, EXTRACT_DOCUMENT_STRUCTURE_PROMPT
from app.core.config import settings
from app.services.llm import generate_content

logger = logging.getLogger(__name__)

async def extract_text_from_document(file_path: str) -> str:
    """
    Extract text from various document formats using the appropriate parser.

    Args:
        file_path: Path to the document file.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If the file format is unsupported.
        Exception: If extraction fails.
    """
    file_extension = Path(file_path).suffix.lower()
    try:
        if file_extension == ".pdf":
            return extract_from_pdf(file_path)
        elif file_extension in [".docx", ".doc"]:
            return extract_from_word(file_path)
        elif file_extension in [".txt", ".md"]:
            return extract_from_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")

def chunk_document(text: str) -> List[str]:
    """
    Split the document text into manageable chunks for processing.

    Args:
        text: Full document text.

    Returns:
        A list of text chunks.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    chars_per_token = 4  # Approximate estimation

    for para in paragraphs:
        if not para.strip():
            continue
        para_tokens = len(para) // chars_per_token
        if current_length + para_tokens > settings.MAX_CHUNK_TOKENS and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_length = para_tokens
        else:
            current_chunk.append(para)
            current_length += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    return chunks

async def analyze_content_per_section(chunks: List[str]) -> List[str]:
    """
    Process each text chunk to extract key information.

    Args:
        chunks: List of document chunks.

    Returns:
        A list of analysis results for each chunk.
    """
    async def process_chunk(chunk: str) -> str:
        prompt = f"{PROCESS_CHUNK_PROMPT}{chunk}"
        response = await generate_content(prompt, system_prompt=SYSTEM_PROMPT)
        return response

    # Process chunks in parallel using ThreadPoolExecutor
    chunk_summaries = []
    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        # Create a list of futures
        futures = [executor.submit(lambda c=chunk: process_chunk(c)) for chunk in chunks]
        
        # Wait for all futures to complete and collect results
        for future in futures:
            chunk_summaries.append(await future.result())
    
    return chunk_summaries

async def generate_coherent_summary(
    content_analysis: List[str], file_path: str
) -> Tuple[str, Path]:
    """
    Generate a coherent summary based on the content analysis.

    Args:
        content_analysis: List of analysis results from document chunks.
        file_path: Original file path (used to generate a summary file name).

    Returns:
        A tuple containing the summary text and the summary file path.
    """
    # If there's only one chunk, no need to call the LLM again
    if len(content_analysis) == 1:
        base_name = Path(file_path).stem
        summary_filename = f"{base_name}_summary.md"
        summary_dir = Path(settings.SUMMARY_RESULTS_DIR)
        summary_dir.mkdir(exist_ok=True)
        summary_path = summary_dir / summary_filename
        return content_analysis[0], summary_path
    
    context = {"analysis": content_analysis}
    context_json = json.dumps(context, indent=2)

    exec_prompt = f"""
    Using the provided analysis of the document chunks, create a unique, reorganized summary.

    Document Chunk Analysis:
    {context_json}

    Please provide the result in Markdown format.
    """
    
    summary = await generate_content(exec_prompt)
    
    base_name = Path(file_path).stem
    summary_filename = f"{base_name}_summary.md"
    summary_dir = Path(settings.SUMMARY_RESULTS_DIR)
    summary_dir.mkdir(exist_ok=True)
    summary_path = summary_dir / summary_filename
    
    # Write summary to file
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    
    return summary, summary_path

async def summarize_folder(folder_path: str) -> List[Dict[str, Any]]:
    """
    Process all supported documents in a folder and generate summaries.

    Args:
        folder_path: Path to the folder containing documents.

    Returns:
        A list of dictionaries with summary results for each document.
    """
    results = []
    folder = Path(folder_path)
    supported_extensions = [".pdf", ".docx", ".doc", ".txt", ".md"]
    files = [f for f in folder.glob("**/*") if f.is_file() and f.suffix.lower() in supported_extensions]

    if not files:
        logger.info(f"No supported documents found in {folder_path}")
        return results

    logger.info(f"Found {len(files)} documents to process in {folder_path}")

    for file_path in files:
        logger.info(f"Processing {file_path}...")
        try:
            # Extract text
            text = await extract_text_from_document(str(file_path))
            
            # Chunk document and analyze content
            chunks = chunk_document(text)
            content_analysis = await analyze_content_per_section(chunks)
            
            # Generate summary
            summary_result, summary_path = await generate_coherent_summary(
                content_analysis, str(file_path)
            )
            
            result = {
                "file_path": str(file_path),
                "summary": summary_result,
                "summary_path": str(summary_path)
            }
            
            logger.info(f"Summary for {file_path} written to {summary_path}")
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            result = {
                "file_path": str(file_path),
                "error": str(e)
            }
            
        results.append(result)
        
    return results