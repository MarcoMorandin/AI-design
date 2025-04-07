from pathlib import Path
import fitz
import docx
import os
from utils import *

def extract_text_from_document(file_path: str) -> str:
    """
    Extract text from various document formats using appropriate parser
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text content
    """
    file_extension = Path(file_path).suffix.lower()
    
    try:
        if file_extension == '.pdf':
            return extract_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return extract_from_word(file_path)
        elif file_extension in ['.txt', '.md']:
            return extract_from_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")

text=extract_text_from_document("test.pdf")
with open("test_extract_text.txt", "w", encoding="utf-8") as f:
    f.write(text)
    