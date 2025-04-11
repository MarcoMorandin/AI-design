# app/services/document_processing.py
import logging
import json
from pathlib import Path
from typing import List

from app.utils.file_handler import extract_from_pdf, extract_from_word, extract_from_text, extract_pdf_content
from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

async def extract_text_from_document(file_name: str) -> str:
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
    file_extension = Path(file_name).suffix.lower()
    try:
        if file_extension == ".pdf":
            return extract_pdf_content(file_name)
        elif file_extension in [".docx", ".doc"]:
            return extract_from_word(file_name)
        elif file_extension in [".txt", ".md"]:
            return extract_from_text(file_name)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")


def chunk_document(text: str) -> List[str]:
    """
    Suddivide il testo del documento in chunk gestibili per l'elaborazione,
    introducendo anche un overlapping tra i chunk in base al valore impostato in settings.OVERLAP.
    
    Args:
        text: Testo completo del documento.
    
    Returns:
        Una lista di chunk di testo.
            tokens = text.split()
    chunks = []
    start = 0

    while start < len(tokens)*4:
        # Determine the end index for the current chunk.
        end = start + (settings.MAX_TOKEN_PER_CHUNK//4)
        chunk_tokens = tokens[start:end]
        chunk = " ".join(chunk_tokens)
        chunks.append(chunk)

        if end >= len(tokens)*4:
            break
        
        # Prepare the starting index for the next chunk.
        start = end - (settings.CHUNK_OVERLAP_TOKEN//4)
    with open("chunks.json", "w") as f:
        json.dump(chunks, f, indent=4)
    return chunks
    """

    #paragraphs = text.split("")
    chunks = []
    current_chunk = []
    current_length = 0
    chars_per_token = 4  # Stima approssimativa: 4 caratteri per token
    if len(text) < settings.MAX_TOKEN_PER_CHUNK:
        chunks.append(text)
        return chunks
    start=0
    while start < len(text):
        end = min(start + settings.MAX_TOKEN_PER_CHUNK, len(text))
        chunks.append(text[start:end])
        start += settings.MAX_TOKEN_PER_CHUNK - settings.CHUNK_OVERLAP_TOKEN
        if end==len(text): break
    return chunks
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # token estimation
        para_tokens = len(para) // chars_per_token
        
        # chunkization
        if current_length + para_tokens > settings.MAX_TOKEN_PER_CHUNK and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
            # Estrazione del pezzo da sovrapporre: si iterano i paragrafi del chunk corrente al contrario
            # fino a raggiungere almeno overlap_tokens token
            overlap_chunk = []
            overlap_count = 0
            for prev_para in reversed(current_chunk):
                # Inserisco all'inizio per mantenere l'ordine originale
                overlap_chunk.insert(0, prev_para)
                overlap_count += len(prev_para) // chars_per_token
                if overlap_count >= settings.CHUNK_OVERLAP_TOKEN:
                    break
            
            # Il nuovo chunk parte dall'overlap
            current_chunk = overlap_chunk.copy()
            current_length = overlap_count
        
        current_chunk.append(para)
        current_length += para_tokens
    with open("chunks.json", "w") as f:
        json.dump(chunks, f, indent=4)

    #if current_chunk:
    #    chunks.append("\n\n".join(current_chunk))
    
    return current_chunk

def extract_markdown(text):
    # Common Markdown start indicators
    start_indicators = ['#', '-', '*', '>', '1.', '```']
    
    # Split the text into lines
    lines = text.splitlines()
    
    # Find the start of the Markdown
    start = 0
    for i, line in enumerate(lines):
        cleaned_line = line.strip()
        if cleaned_line:  # Ignore empty lines
            if any(cleaned_line.startswith(indicator) for indicator in start_indicators) or cleaned_line.isalnum():
                start = i
                break
    
    # If no start is found, return an empty string
    if start >= len(lines):
        return ""
    
    # Find the end of the Markdown
    end = len(lines)
    in_code_block = False
    consecutive_empty_lines = 0
    
    for i in range(start, len(lines)):
        line = lines[i].strip()
        
        # Handle code blocks (```)
        if line.startswith('```'):
            in_code_block = not in_code_block
            continue
        
        # If we are outside a code block
        if not in_code_block:
            if not line:  # Empty line
                consecutive_empty_lines += 1
                if consecutive_empty_lines >= 2:  # Two consecutive empty lines indicate a possible end
                    end = i
                    break
            else:
                # If the line doesn't look like Markdown and isn't a simple paragraph, it might be the end
                if not any(line.startswith(indicator) for indicator in start_indicators) and not line.isalnum():
                    end = i
                    break
                consecutive_empty_lines = 0  # Reset if we find meaningful content
    
    # Return the text between start and end
    markdown_text = '\n'.join(lines[start:end])
    return markdown_text.strip()