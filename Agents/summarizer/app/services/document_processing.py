import logging
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF
import comtypes.client
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
#from app.utils.file_handler import extract_from_pdf, extract_from_word, extract_from_text, extract_pdf_content
import os
from app.core.config import settings
import requests
import torch
from app.utils.chucker.standardar_chuncker import chunk_document as standardar_chuncker
from app.utils.chucker.cosine_chuncker import chunk_document_cosine as cosine_chuncker

logger = logging.getLogger(__name__)

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
        elif file_extension in [".ppt"]:
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

def _convert_to_pdf(file_name, application_type):
    path_without_extension = os.path.splitext(file_path)[0]
    word = comtypes.client.CreateObject(application_type)
    word.Visible = False
    doc = word.Documents.Open(file_name)
    doc.SaveAs(path_without_extension+".pdf", FileFormat=17) # 17 is PDF format
    doc.Close()
    word.Quit()

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
            # reverse order otherwise the char_offset increse after inserting the caption
        #for img_caption in images_caption[::-1]:
        #    response=_insert_img_caption(response.text, img_caption)
        with open('test_ocr.mmd', 'w') as md_file:
            md_file.write(response.json())
        return response.json()
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


def get_image_info(file_name: str) -> List[Dict[int, str]]:
    image_positions = []
        
    try:
        # Open PDF
        doc = fitz.open(Path(file_name))

        for page_num, page in enumerate(doc):
            # Ottieni blocchi di testo con informazioni di formattazione
            blocks = page.get_text("dict")["blocks"]
            # sort by reading order
            sorted_blocks = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
            char_count = 0
            images_in_page = [] # image info
            
            for block in sorted_blocks:
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        # concat text
                        line_text = "".join(span["text"] for span in line["spans"])
                        char_count += len(line_text)
                
                elif block["type"] == 1:  # image block
                    xref = block.get("image", 0) or block.get("xref", 0)
                    if xref and isinstance(xref, int):  # Ensure xref is an integer
                        try:
                            # Estrazione dell'immagine dal PDF
                            base_image = doc.extract_image(xref)
                            if base_image and "image" in base_image:
                                image_bytes = base_image["image"]
                                image_caption = _generate_caption_with_blip(Image.open(io.BytesIO(image_bytes)))
                                images_in_page.append({
                                    "char_offset": char_count,
                                    "img_caption": image_caption,
                                })
                        except Exception as img_error:
                            logger.warning(f"Failed to process image on page {page_num+1}, xref {xref}: {img_error}")
            
            image_positions.append(images_in_page)

        doc.close()
        return image_positions
        
    except Exception as e:
        logger.error(f"Errore nell'estrazione del testo: {e}")
        return []  # Return empty list instead of empty dict to match return type


def _generate_caption_with_blip(byte_image):
    try:

        model_name = "Salesforce/blip-image-captioning-base"
        processor = BlipProcessor.from_pretrained(model_name)
        model = BlipForConditionalGeneration.from_pretrained(model_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()

        with torch.no_grad():

            # Conditional caption
            conditional_inputs = processor(byte_image, text="Describe the imag", return_tensors="pt").to(device)
            with autocast():
                conditional_outputs = model.generate(**conditional_inputs)
            conditional_caption = processor.decode(conditional_outputs[0], skip_special_tokens=True)

        return conditional_caption

    except Exception as e:
        logger.error(f"Errore nell'estrazione del testo: {e}")
        return []  # Return empty list instead of empty dict to match return type