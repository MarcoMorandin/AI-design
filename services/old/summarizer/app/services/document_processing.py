import logging
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF
import comtypes.client
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
#from app.utils.file_handler import extract_from_pdf, extract_from_word, extract_from_text, extract_pdf_content
import os
import io
from app.core.config import settings
import requests
import torch
from app.utils.chucker.standardar_chuncker import chunk_document as standardar_chuncker
from app.utils.chucker.cosine_chuncker import chunk_document_cosine as cosine_chuncker

logger = logging.getLogger(__name__)

model_name = settings.IMAGE_DESCRIPTION_EXTRACTION_MODEL
processor = BlipProcessor.from_pretrained(model_name)
model = BlipForConditionalGeneration.from_pretrained(model_name)

async def extract_text_from_document(file_name: str, images_caption) -> str:
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
            return extract_pdf_content(file_name, images_caption)
        elif file_extension in [".docx", ".doc"]:
            return extract_pdf_content(_convert_to_pdf(file_name, "Word.Application"), images_caption)
        elif file_extension in [".ppt", ".pptx"]:
            return extract_pdf_content(_convert_to_pdf(file_name, "Powerpoint.Application"), images_caption)
        elif file_extension in [".txt", ".md"]:
            return _extract_from_text(file_name)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")

def _extract_from_text(file_name):

    with open(file_name, 'r') as file:
        content = file.read()

    return content

def _convert_to_pdf(file_path, application_type):
    path_without_extension = os.path.splitext(file_path)[0]
    pdf_path = path_without_extension + ".pdf"
    
    app = comtypes.client.CreateObject(application_type)
    
    if application_type == "Word.Application":
        app.Visible = False
        doc = app.Documents.Open(os.path.abspath(file_path))
        doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)  # 17 is PDF format
        doc.Close()
    elif application_type == "PowerPoint.Application":
        # For PowerPoint, don't set Visible = False as it causes errors
        presentation = app.Presentations.Open(os.path.abspath(file_path), WithWindow=False)
        presentation.SaveAs(os.path.abspath(pdf_path), 32)  # 32 is PDF format for PowerPoint
        presentation.Close()
    
    app.Quit()
    return pdf_path

def extract_pdf_content(file_path: str, images_caption) -> str:
    """
    Estrae il testo dal file PDF specificato.

    Args:
        file_name: Nome del file PDF.

    Returns:
        Testo estratto dal file PDF.

    Raises:
        Exception: Se si verifica un errore durante l'estrazione del testo.
    """
    try:
        str_file_path=str(file_path)
        with open(str_file_path, 'rb') as f:
            files = {'file': (str_file_path, f, 'application/pdf')}
            response = requests.post("http://127.0.0.1:8503/predict/", files=files)

        response=response.json()
        # reverse order otherwise the char_offset increse after inserting the caption
        for img_caption in images_caption[::-1]:
            response=_insert_img_caption(response, img_caption)
        # just to check
        with open('test_ocr.mmd', 'w') as md_file:
            md_file.write(response)

        return response
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")


def chunk_document_cosine(text:str)->List[str]:
    logger.info("Cosine chucnker")
    return cosine_chuncker(text)

def _insert_img_caption(text, img_caption):
    temp_text = [text[:img_caption['char_offset']], img_caption['img_caption'], text[img_caption['char_offset']:]]
    return ''.join(temp_text)


def chunk_document(text: str) -> List[str]:
    """
    Suddivide il testo del documento in chunk gestibili per l'elaborazione,
    introducendo anche un overlapping tra i chunk in base al valore impostato in settings.OVERLAP.
    
    Args:
        text: Testo completo del documento.
    
    Returns:
        Una lista di chunk di testo
    """
    return standardar_chuncker(text)


def get_image_info(file_name: str) -> List[Dict]:
    image_captions = []
    try:
        # Open PDF
        doc = fitz.open(Path(file_name))

        for page_num, page in enumerate(doc):
            # Ottieni blocchi di testo con informazioni di formattazione
            text = page.get_text()
            char_count = len(text)
            image_list = page.get_images()  # Changed from getImageList() to get_images()
            
            if not image_list:
                logger.info(f"No images found on page {page_num+1}")
                continue
                
            for image_index, img in enumerate(image_list, start=1):
                # get the XREF of the image
                xref = img[0]
                try:
                    # extract the image bytes
                    base_image = doc.extract_image(xref)  # Changed from extractImage to extract_image
                    image_bytes = base_image["image"]
                    
                    # Process the image
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    image_caption = _generate_caption_with_blip(pil_image)
                    
                    image_captions.append({
                        "char_offset": char_count,
                        "img_caption": " Image description: "+image_caption,
                    })
                    logger.info(f"Processed image {image_index} on page {page_num+1}")
                except Exception as e:
                    logger.error(f"Error processing image {image_index} on page {page_num+1}: {e}")
        
        doc.close()
        return image_captions
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return []


def _generate_caption_with_blip(pil_image):
    global processor, model
    
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()

        with torch.no_grad():
            # Conditional caption
            conditional_inputs = processor(pil_image, text="Describe the image", return_tensors="pt").to(device)
            with autocast():
                conditional_outputs = model.generate(**conditional_inputs)
            conditional_caption = processor.decode(conditional_outputs[0], skip_special_tokens=True)

        return conditional_caption

    except Exception as e:
        logger.error(f"Error generating caption: {e}")
        return "No caption available"  # Return a default string instead of empty list