from typing import Dict, Any, List
import logging
import re
import sys
import os

# Add the parent directory to the path to import utils
sys.path.append(os.path.dirname(__file__) + "/..")
from utils import sanitize_content

logger = logging.getLogger(__name__)


async def chunk_markdown(content: str, chunk_size: int = 800) -> Dict[str, Any]:
    """
    Splits a markdown document into smaller chunks.

    This function attempts to intelligently chunk the document by preserving
    the structure of headings, paragraphs, and other markdown elements.

    Args:
        content: The markdown content to be chunked
        chunk_size: Maximum size of each chunk in characters (default: 800)

    Returns:
        Dict containing a list of markdown chunks

    Tool:
        name: chunk_markdown
        description: Splits a markdown document into smaller, semantically meaningful chunks
        input_schema:
            type: object
            properties:
                content:
                    type: string
                    description: The markdown content to be chunked
                chunk_size:
                    type: integer
                    description: Maximum size of each chunk in characters
                    default: 800
            required:
                - content
        output_schema:
            type: object
            properties:
                chunks:
                    type: array
                    description: List of markdown chunks
                    items:
                        type: string
                success:
                    type: boolean
                    description: Whether the operation was successful
                message:
                    type: string
                    description: Status message or error information
    """
    try:
        logger.info(f"Chunking markdown content of size {len(content)}")

        # Validate input content
        if not content or not content.strip():
            logger.warning("Empty or None content provided to chunk_markdown")
            return {
                "success": False,
                "chunks": [],
                "message": "No content provided to chunk",
            }

        # Sanitize content to remove invalid control characters
        content = sanitize_content(content)
        
        if not content:
            logger.warning("Content is empty after sanitization")
            return {
                "success": False,
                "chunks": [],
                "message": "Content is empty after removing invalid characters",
            }

        # If content is smaller than chunk size, return it as a single chunk
        if len(content) <= chunk_size:
            return {
                "success": True,
                "chunks": [content],
                "message": "Content did not need chunking",
            }

        # Simple chunking approach - split by paragraphs first, then by sentences if needed
        chunks = []
        current_chunk = ""
        
        # Try to split by double newlines (paragraphs) first
        paragraphs = re.split(r'\n\s*\n', content)
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If adding this paragraph would exceed chunk size
            if len(current_chunk + "\n\n" + paragraph) > chunk_size and current_chunk:
                # Save current chunk and start a new one
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            elif len(paragraph) > chunk_size:
                # If current chunk has content, save it first
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split large paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk + " " + sentence) > chunk_size and temp_chunk:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = sentence
                    else:
                        temp_chunk = (temp_chunk + " " + sentence).strip()
                
                # Add remaining sentences as current chunk
                if temp_chunk:
                    current_chunk = temp_chunk
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Fallback: if no chunks were created, split by character count
        if not chunks:
            logger.warning("Fallback to character-based chunking")
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())

        logger.info(f"Successfully chunked content into {len(chunks)} chunks")

        return {
            "success": True,
            "chunks": chunks,
            "message": f"Content chunked into {len(chunks)} parts",
        }

    except Exception as e:
        logger.error(f"Error chunking markdown: {str(e)}")
        return {
            "success": False,
            "chunks": [],
            "message": f"Error chunking markdown: {str(e)}",
        }
