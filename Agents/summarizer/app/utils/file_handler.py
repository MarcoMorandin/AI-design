import fitz  # PyMuPDF
from docx import Document
from typing import Dict, Any
import logging
import zipfile  # Importato per estrarre i file da un DOCX (che è un file ZIP)
from pathlib import Path
from app.core.config import settings


logger = logging.getLogger(__name__)

# Try to import easyocr per estrazione testo dalle immagini
try:
    import easyocr
    reader = easyocr.Reader(['en', 'it'])
    OCR_AVAILABLE = True
except ImportError:
    logger.warning("easyocr non installato. L'estrazione del testo dalle immagini non sarà disponibile.")
    OCR_AVAILABLE = False

def extract_from_pdf(file_name: str) -> str:
    """Estrae il testo dai documenti PDF, includendo il testo ottenuto da immagini (se OCR è disponibile)."""
    try:
        
        doc = fitz.open(Path(settings.TEMP_DIR) / f"{file_name}")
        text_blocks = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # extract text
            text_blocks.append(page.get_text())

            # Extract text from image id OCR available
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
                        text_blocks.append(f"[{image_text.strip()}]")
        # unify blocks
        return "\n\n".join(text_blocks)
    except ImportError:
        raise ImportError("La libreria PyMuPDF (fitz) è richiesta per l'estrazione da PDF. Installala con 'pip install pymupdf'")
    except Exception as e:
        logger.error(f"Errore durante l'estrazione del testo dal PDF: {str(e)}")
        raise

def extract_from_word(file_path: str) -> str:
    """Estrae il testo e, se possibile, il contenuto testuale dalle immagini dai documenti Word."""
    try:
        # Extract text
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text_blocks = paragraphs.copy()

        #extrct images id OCR available
        try:
            with zipfile.ZipFile(file_path) as docx_zip:
                for file in docx_zip.namelist():
                    if file.startswith("word/media/"):
                        image_bytes = docx_zip.read(file)
                        if OCR_AVAILABLE:
                            result = reader.readtext(image_bytes)
                            image_text = " ".join([text for (_, text, prob) in result if prob > 0.25])
                            if image_text:
                                text_blocks.append(f"[{image_text.strip()}]")
        except Exception as e:
            logger.error(f"Errore durante l'estrazione delle immagini dal documento Word: {str(e)}")

        return "\n\n".join(text_blocks)
    except ImportError:
        raise ImportError("La libreria python-docx è richiesta per l'estrazione da Word. Installala con 'pip install python-docx'")
    except Exception as e:
        logger.error(f"Errore nell'estrazione dal documento Word: {str(e)}")
        raise

def extract_from_text(file_path: str) -> str:
    """Extract text from plain text files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error extracting text from text file: {str(e)}")
        raise


#### NOT USED

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