from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)


async def chunk_markdown(content: str, chunk_size: int = 2000) -> Dict[str, Any]:
    """
    Splits a markdown document into smaller chunks.

    This function attempts to intelligently chunk the document by preserving
    the structure of headings, paragraphs, and other markdown elements.

    Args:
        content: The markdown content to be chunked
        chunk_size: Maximum size of each chunk in characters (default: 2000)

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
                    default: 2000
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

        # If content is smaller than chunk size, return it as a single chunk
        if len(content) <= chunk_size:
            return {
                "success": True,
                "chunks": [content],
                "message": "Content did not need chunking",
            }

        # Split by headings first (# headings)
        heading_pattern = r"(^|\n)(#{1,6} .+)(\n|$)"
        sections = re.split(heading_pattern, content, flags=re.MULTILINE)

        # Process the sections
        chunks = []
        current_chunk = ""

        i = 0
        while i < len(sections):
            # If this is a heading match from the regex split
            if i > 0 and i % 4 == 2:
                heading = sections[i]
                content_after_heading = sections[i + 1] if i + 1 < len(sections) else ""

                # Check if adding this section would exceed chunk size
                potential_chunk = current_chunk + heading + content_after_heading

                if len(potential_chunk) <= chunk_size:
                    current_chunk = potential_chunk
                else:
                    # If current chunk is not empty, add it to chunks
                    if current_chunk:
                        chunks.append(current_chunk)

                    # If the heading + content is larger than chunk_size, we need to split further
                    if len(heading + content_after_heading) > chunk_size:
                        # Add the heading to the new chunk
                        current_chunk = heading

                        # Split the content into paragraphs
                        paragraphs = re.split(r"\n\s*\n", content_after_heading)

                        for paragraph in paragraphs:
                            if len(current_chunk + paragraph + "\n\n") <= chunk_size:
                                current_chunk += paragraph + "\n\n"
                            else:
                                # If current chunk is not empty, add it to chunks
                                if current_chunk:
                                    chunks.append(current_chunk)

                                # If paragraph itself is too large, split it by sentences
                                if len(paragraph) > chunk_size:
                                    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                                    current_chunk = ""

                                    for sentence in sentences:
                                        if (
                                            len(current_chunk + sentence + " ")
                                            <= chunk_size
                                        ):
                                            current_chunk += sentence + " "
                                        else:
                                            chunks.append(current_chunk)
                                            current_chunk = sentence + " "
                                else:
                                    current_chunk = paragraph + "\n\n"
                    else:
                        # Start a new chunk with this heading
                        current_chunk = heading + content_after_heading

                i += 2  # Skip the content part as we've already processed it
            else:
                # For other parts of the split (content before first heading or between heading matches)
                section = sections[i]

                if len(current_chunk + section) <= chunk_size:
                    current_chunk += section
                else:
                    if current_chunk:
                        chunks.append(current_chunk)

                    # If this section is larger than chunk_size, split it further
                    if len(section) > chunk_size:
                        paragraphs = re.split(r"\n\s*\n", section)
                        current_chunk = ""

                        for paragraph in paragraphs:
                            if len(current_chunk + paragraph + "\n\n") <= chunk_size:
                                current_chunk += paragraph + "\n\n"
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk)

                                # If paragraph itself is too large, split it by sentences
                                if len(paragraph) > chunk_size:
                                    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                                    current_chunk = ""

                                    for sentence in sentences:
                                        if (
                                            len(current_chunk + sentence + " ")
                                            <= chunk_size
                                        ):
                                            current_chunk += sentence + " "
                                        else:
                                            chunks.append(current_chunk)
                                            current_chunk = sentence + " "
                                else:
                                    current_chunk = paragraph + "\n\n"
                    else:
                        current_chunk = section

                i += 1

        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(current_chunk)

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
