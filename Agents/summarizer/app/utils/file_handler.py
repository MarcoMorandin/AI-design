# app/utils/file_handler.py
import fitz  # PyMuPDF
from docx import Document
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Try to import easyocr for image text extraction
try:
    import easyocr
    reader = easyocr.Reader(['en', 'it'])
    OCR_AVAILABLE = True
except ImportError:
    logger.warning("easyocr not installed. Image text extraction will not be available.")
    OCR_AVAILABLE = False

def extract_from_pdf(file_path: str) -> str:
    """Extract text from PDF documents."""
    try:
        doc = fitz.open(file_path)
        text_blocks = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text
            text_blocks.append(page.get_text())

            # Extract images if OCR is available
            if OCR_AVAILABLE:
                for img_index, img in enumerate(page.get_images()):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    result = reader.readtext(image_bytes)
                    image_text = ""
                    for (bbox, text, prob) in result:
                        if prob > 0.25:
                            image_text += f"{text} "
                    if image_text:
                        text_blocks.append(f"content_img_page{page_num+1}: [{image_text}]")

        return "\n\n".join(text_blocks)
    except ImportError:
        raise ImportError("PyMuPDF (fitz) library is required for PDF extraction. Install with 'pip install pymupdf'")
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def extract_from_word(file_path: str) -> str:
    """Extract text from Word documents."""
    try:
        doc = Document(file_path)
        return "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except ImportError:
        raise ImportError("python-docx library is required for Word extraction. Install with 'pip install python-docx'")
    except Exception as e:
        logger.error(f"Error extracting text from Word document: {str(e)}")
        raise

def extract_from_text(file_path: str) -> str:
    """Extract text from plain text files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error extracting text from text file: {str(e)}")
        raise

def get_document_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from document."""
    file_extension = file_path.lower().split('.')[-1]
    metadata = {
        "filename": file_path.split('/')[-1],
        "file_type": file_extension,
    }
    
    try:
        if file_extension == "pdf":
            doc = fitz.open(file_path)
            metadata["page_count"] = len(doc)
            # Add more PDF metadata as needed
            
        elif file_extension in ["docx", "doc"]:
            doc = Document(file_path)
            # Estimate word count
            word_count = sum(len(para.text.split()) for para in doc.paragraphs)
            metadata["word_count"] = word_count
            # Add more Word metadata as needed
            
        elif file_extension in ["txt", "md"]:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                metadata["word_count"] = len(text.split())
    except Exception as e:
        logger.warning(f"Error extracting metadata from {file_path}: {str(e)}")
        
    return metadata