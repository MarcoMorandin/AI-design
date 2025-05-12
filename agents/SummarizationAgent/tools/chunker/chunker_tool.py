from .chunker_types.standardar_chuncker import chunk_document
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_chunks(text: str) -> List[str]:
    """
    Splits the input text into chunks using a standard algorithm that divides text into fixed-size chunks.

    Args:
        text (str): The input text to be chunked.

    Returns:
        List[str]: A list of text chunks.
    """
    logger.info(f"Chunking text of length: {len(text)} characters")

    try:
        chunks = chunk_document(text)
        logger.info(f"Successfully created {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error during chunking: {str(e)}")
        # Fallback to simple chunking if the standard chunker fails
        if len(text) > 4000:
            return [text[i : i + 4000] for i in range(0, len(text), 3500)]
        else:
            return [text]
