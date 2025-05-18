from typing import List, Dict, Any, Optional
from ..core.config import settings
from sklearn.metrics.pairwise import cosine_similarity
import torch
import torch.nn.functional as F
from .standardar_chuncker import chunk_document
import traceback
from google import genai
from google.genai import types
import os
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Google Gemini client
try:


    # Initialize client with API key from settings
    if settings.GEMINI_API_KEY:
        #genai.configure(api_key=settings.GEMINI_API_KEY)
        embedding_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        #embedding_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        #llm_client = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        embedding_model = settings.GEMINI_EMBEDDING_MODEL
        GEMINI_AVAILABLE = True
        logger.info(
            f"Successfully initialized Gemini API client with model: {settings.GEMINI_MODEL_NAME}"
        )
    else:
        logger.warning("GEMINI_API_KEY not provided in environment variables")
        GEMINI_AVAILABLE = False
except ImportError:
    logger.warning(
        "Google Gemini package not installed. Cosine chunking will use fallback methods."
    )
    GEMINI_AVAILABLE = False
except Exception as e:
    logger.error(f"Error initializing Gemini client: {str(e)}")
    GEMINI_AVAILABLE = False


def chunk_document_cosine(text: str) -> List[str]:
    """
    Splits text into semantically coherent chunks using cosine similarity
    to determine appropriate chunk boundaries.

    Args:
        text (str): Input text to chunk

    Returns:
        List[str]: List of chunked text segments
    """
    if not text or not isinstance(text, str):
        logger.error("Invalid input to cosine chunker: text must be non-empty string")
        raise ValueError("Text must be a non-empty string")

    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API not available. Falling back to standard chunking.")
        return chunk_document(text)

    try:
        logger.info(f"Starting cosine chunking for text of length {len(text)}")

        # Get initial chunks using standard chunker
        chunks = get_initial_chunks(text)

        if len(chunks) <= 1:
            logger.info(
                "Text is small enough for a single chunk, skipping cosine processing"
            )
            return [chunk["section"] for chunk in chunks] if chunks else [text]

        # Calculate semantic distances between chunks
        distances, chunks = _cosine_distance(chunks)

        # Find breakpoints based on semantic distance threshold
        indices_above_threshold = _indices_above_threshold_distance(distances)

        # Group chunks based on these breakpoints
        chunks = _group_chunks(indices_above_threshold, chunks)

        # Clean up artifacts from the chunking process
        chunks = _remove_artifacts(chunks)

        logger.info(f"Cosine chunking complete, created {len(chunks)} semantic chunks")
        return chunks

    except Exception as e:
        logger.error(f"Error during cosine chunking: {str(e)}")
        logger.debug(f"Exception details: {traceback.format_exc()}")
        logger.warning("Falling back to standard chunking method")
        return chunk_document(text)


def get_initial_chunks(text: str) -> List[Dict[str, Any]]:
    """
    Creates initial chunks from text using standard chunking algorithm
    and prepares them for semantic analysis.

    Args:
        text: Input text to process

    Returns:
        List of dictionaries containing chunk data
    """
    try:
        # Get base chunks using standard chunker
        raw_chunks = chunk_document(text)

        # Convert to dictionary format with metadata
        chunks = [{"sentence": x, "index": i} for i, x in enumerate(raw_chunks)]

        # Combine with neighboring sentences for better semantic context
        chunks = _combine_sentences(chunks, 1)

        # Add embeddings to chunks
        chunks = _do_embedding(chunks)

        return chunks

    except Exception as e:
        logger.error(f"Error preparing initial chunks: {str(e)}")
        # Return minimal chunks if there's an error
        return [{"sentence": text, "section": text, "index": 0}]


def _remove_artifacts(chunks):
    """
    Removes internal metadata and returns clean text chunks.

    Args:
        chunks: List of chunk dictionaries with metadata

    Returns:
        List of cleaned text chunks
    """
    result = []

    for chunk in chunks:
        # For production, defensively check for expected structure
        if isinstance(chunk, dict):
            if "section" in chunk:
                result.append(chunk["section"])
            elif "sentence" in chunk:
                result.append(chunk["sentence"])

    return result


def _group_chunks(indices, sentences):
    """
    Groups chunks based on semantic breakpoints identified by cosine similarity.

    Args:
        indices: List of breakpoint indices
        sentences: List of sentence dictionaries

    Returns:
        List of grouped chunks
    """
    # Initialize the start index
    start_index = 0
    # Create a list to hold the grouped sentences
    final_chunks = []

    try:
        # Iterate through the breakpoints to slice the sentences
        for index in indices:
            # The end index is the current breakpoint
            end_index = index
            # Slice the sentence_dicts from the current start index to the end index
            group = sentences[start_index : end_index + 1]
            combined_text = " ".join(
                [d.get("sentence", "") for d in group if isinstance(d, dict)]
            )
            final_chunks.extend(_check_len([combined_text]))
            start_index = index + 1

        # Process the last group, if any sentences remain
        if start_index < len(sentences):
            combined_text = " ".join(
                [
                    d.get("sentence", "")
                    for d in sentences[start_index:]
                    if isinstance(d, dict)
                ]
            )
            final_chunks.extend(_check_len([combined_text]))

        return final_chunks

    except Exception as e:
        logger.error(f"Error grouping chunks: {str(e)}")
        # Return original sentences as fallback
        return [
            {"sentence": s.get("sentence", ""), "section": s.get("sentence", "")}
            for s in sentences
            if isinstance(s, dict)
        ]


def _check_len(chunk):
    """
    Checks if chunks exceed token limits and splits if necessary.

    Args:
        chunk: Text chunk to check

    Returns:
        List of chunks within token limits
    """
    if not GEMINI_AVAILABLE:
        # Estimate token count (roughly 4 chars per token)
        estimated_tokens = sum(len(text) // 4 for text in chunk)
        if estimated_tokens > settings.MAX_TOKEN_PER_CHUNK_GROUPED:
            return _get_new_chunk(len(chunk), chunk)
        else:
            return _get_new_chunk(1, chunk)

    try:
        # Get actual token count from API
        token_count = genai.count_tokens(
            model=settings.GEMINI_MODEL_NAME, text=chunk[0] if chunk else ""
        )
        total_tokens = token_count.total_tokens

        # Check if the amount of tokens exceeds the limit
        if total_tokens > settings.MAX_TOKEN_PER_CHUNK_GROUPED:
            docs_split = chunk_document(chunk[0] if chunk else "")
            # Get new embeddings for the new chunks
            return _get_new_chunk(len(docs_split), docs_split)
        else:
            return _get_new_chunk(1, chunk)

    except Exception as e:
        logger.warning(f"Error checking token length: {str(e)}")
        # Fallback to simple estimation
        return _get_new_chunk(1, chunk)


def _get_new_chunk(leng, chunks):
    """
    Creates new chunk objects from raw text.

    Args:
        leng: Number of chunks
        chunks: Text content for chunks

    Returns:
        List of chunk objects with embeddings
    """
    splitted_chunks = []

    try:
        # Get strings from documents
        if isinstance(chunks, list) and len(chunks) == 1 and isinstance(chunks[0], str):
            string_text = [chunks[0] for _ in range(leng)]
        elif all(isinstance(chunk, str) for chunk in chunks):
            string_text = chunks
        else:
            string_text = ["" for _ in range(leng)]

        # Create chunk objects
        chunks_edit = [
            {"sentence": x, "index": i, "section": x} for i, x in enumerate(string_text)
        ]

        # Add embeddings
        chunks_edit = _do_embedding(chunks_edit)

        # Add to result list
        splitted_chunks.extend(chunks_edit)

        return splitted_chunks

    except Exception as e:
        logger.error(f"Error creating new chunks: {str(e)}")
        # Return basic chunks as fallback
        return [
            {"sentence": chunk, "section": chunk}
            for chunk in (chunks if isinstance(chunks, list) else [chunks])
        ]


def _indices_above_threshold_distance(distances, distance_threshold=None):
    """
    Identifies chunk boundaries based on semantic distance threshold.

    Args:
        distances: List of cosine distances between consecutive chunks
        distance_threshold: Optional custom threshold (defaults to 0.95)

    Returns:
        List of indices where chunks should be split
    """
    # Use custom threshold if provided, otherwise use default
    threshold = distance_threshold if distance_threshold is not None else 0.95

    # Higher distance --> fewer chunks
    # Lower distance --> more chunks
    indices_above_thresh = []

    for i, distance in enumerate(distances):
        if (1 - distance) < threshold:
            indices_above_thresh.append(i)

    return indices_above_thresh


def _cosine_distance(chunks):
    """
    Calculates cosine distance between consecutive chunks.

    Args:
        chunks: List of chunk dictionaries with embeddings

    Returns:
        Tuple of (distances, updated_chunks)
    """
    distances = []

    try:
        for i in range(len(chunks) - 1):
            if "embedding" not in chunks[i] or "embedding" not in chunks[i + 1]:
                logger.warning(f"Missing embedding in chunk {i} or {i+1}")
                distances.append(0.5)  # Default middle distance
                continue

            embedding_current = chunks[i]["embedding"]
            embedding_next = chunks[i + 1]["embedding"]

            # Calculate cosine similarity
            similarity = cosine_similarity([embedding_current], [embedding_next])[0][0]

            # Convert to cosine distance
            distance = 1 - similarity

            # Append cosine distance to the list
            distances.append(distance)

            # Store distance in the dictionary
            chunks[i]["distance_to_next"] = distance

        return distances, chunks

    except Exception as e:
        logger.error(f"Error calculating cosine distances: {str(e)}")
        # Return default distances
        return [0.5] * (len(chunks) - 1), chunks


def _do_embedding(chunks):
    """
    Adds embeddings to chunks using the Gemini API.

    Args:
        chunks: List of chunk dictionaries

    Returns:
        Updated chunks with embeddings
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API not available for embeddings")
        # Create mock embeddings (random vectors)
        for chunk in chunks:
            chunk["embedding"] = [0.1] * 50  # Simple mock embedding
        return chunks

    try:
        for i, chunk in enumerate(chunks):
            if "section" not in chunk:
                logger.warning(f"Missing 'section' in chunk {i}")
                chunk["section"] = chunk.get("sentence", "")

            # Get embedding from Gemini API
            result = embedding_client.models.embed_content(
                model=embedding_model,
                contents=[chunk["section"]],
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
            )

            # Extract embedding values
            embedding = result.embeddings[0].values# if hasattr(result, "embedding") else []

            # Store in chunk
            chunks[i]["embedding"] = embedding

        return chunks

    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        # Create fallback embeddings
        for chunk in chunks:
            chunk["embedding"] = [0.1] * 50  # Simple fallback embedding
        return chunks


def _combine_sentences(chunks: List[Dict], buffer_size: int) -> List[Dict]:
    """
    Combines each chunk with surrounding chunks for better contextual understanding.

    Args:
        chunks: List of chunk dictionaries
        buffer_size: Number of chunks before/after to include

    Returns:
        Updated chunks with combined sections
    """
    for i in range(len(chunks)):
        # Create a string for the joined sentences
        combined_sentence = ""

        # Add sentences before the current one, based on buffer size
        for j in range(i - buffer_size, i):
            # Avoid negative indices
            if j >= 0 and j < len(chunks):
                combined_sentence += chunks[j].get("sentence", "") + " "

        # Add current sentence
        current_sentence = chunks[i].get("sentence", "")
        combined_sentence += current_sentence

        # Add sentences after the current one
        for j in range(i + 1, i + 1 + buffer_size):
            if j < len(chunks):
                combined_sentence += " " + chunks[j].get("sentence", "")

        # Store combined text
        chunks[i]["section"] = combined_sentence

    return chunks
