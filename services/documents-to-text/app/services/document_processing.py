import logging
from pathlib import Path
from typing import List, Dict
import fitz
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import os
import io
from app.core.config import settings
import requests
import torch
import subprocess
logger = logging.getLogger(__name__)

model_name = settings.IMAGE_DESCRIPTION_EXTRACTION_MODEL
processor = BlipProcessor.from_pretrained(model_name)
model = BlipForConditionalGeneration.from_pretrained(model_name)

def _extract_from_text(url):

    with open(url, 'r') as file:
        content = file.read()

    return content

def _convert_to_pdf(input_path: str) -> str:
    input_path_obj = Path(input_path)
    output_pdf_path = input_path_obj.with_suffix(".pdf")
    
    # Ensure input path is absolute for pandoc robustness
    abs_input_path = str(input_path_obj.resolve())
    abs_output_pdf_path = str(output_pdf_path.resolve())

    command = [
        "pandoc",
        abs_input_path,
        "-o",
        abs_output_pdf_path,
        "--pdf-engine=xelatex"
    ]
    logger.info(f"Running Pandoc command: {' '.join(command)}")

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)
        logger.info(f"Pandoc successfully converted {input_path_obj.name} to PDF.")
        logger.debug(f"Pandoc stdout: {result.stdout}")
        logger.debug(f"Pandoc stderr: {result.stderr}")
        return abs_output_pdf_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc conversion failed for {input_path_obj.name} with return code {e.returncode}")
        logger.error(f"Pandoc stderr: {e.stderr}")
        raise Exception(f"Pandoc error converting {input_path_obj.name}: {e.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"Pandoc conversion timed out for {input_path_obj.name}")
        raise Exception(f"Pandoc conversion timed out for {input_path_obj.name}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Pandoc conversion: {e}")
        raise Exception(f"Unexpected Pandoc error for {input_path_obj.name}: {str(e)}")


def _generate_caption_with_blip(pil_image):
    global processor, model
    
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()

        with torch.no_grad():
            conditional_inputs = processor(pil_image, text="Describe the image", return_tensors="pt").to(device)
            with torch.autocast():
                conditional_outputs = model.generate(**conditional_inputs)
            conditional_caption = processor.decode(conditional_outputs[0], skip_special_tokens=True)

        return conditional_caption

    except Exception as e:
        logger.error(f"Error generating caption: {e}")
        return "No caption available"
    
def _insert_img_caption(text, img_caption):
    temp_text = [text[:img_caption['char_offset']], img_caption['img_caption'], text[img_caption['char_offset']:]]
    return ''.join(temp_text)


def _get_image_info(url: str) -> List[Dict]:
    image_captions = []
    try:
        # Open PDF
        doc = fitz.open(Path(url))

        for page_num, page in enumerate(doc):
            # Ottieni blocchi di testo con informazioni di formattazione
            text = page.get_text()
            char_count = len(text)
            image_list = page.get_images()  # Changed from getImageList() to get_images()
            
            if not image_list:
                logger.debug(f"No images found on page {page_num+1}")
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


def _extract_pdf_content(file_path: str) -> str:
    try:
        str_file_path=str(file_path)
        with open(str_file_path, 'rb') as f:
            files = {'file': (str_file_path, f, 'application/pdf')}
            response = requests.post(f"{settings.NOUGAT_URL}/predict/", files=files, headers={'x-api-key': settings.NOUGAT_API_KEY})

        response=response.json()
        
        images_caption = _get_image_info(file_path)
        
        for img_caption in images_caption[::-1]:
            response=_insert_img_caption(response, img_caption)

        return response
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")

async def extract_text_from_document(url: str) -> str:
    file_path_obj = Path(url)
    file_extension = file_path_obj.suffix.lower()
    pdf_to_process = None
    converted = False

    try:
        if file_extension == ".pdf":
            pdf_to_process = str(file_path_obj.resolve())
        elif file_extension in [".docx", ".doc", ".ppt", ".pptx"]:
            logger.info(f"Converting {file_path_obj.name} to PDF using Pandoc...")
            pdf_to_process = _convert_to_pdf(str(file_path_obj.resolve()))
            converted = True
            logger.info(f"Successfully converted to {pdf_to_process}")
        elif file_extension in [".txt", ".md"]:
             logger.info(f"Reading text directly from {file_path_obj.name}")
             return _extract_from_text(str(file_path_obj.resolve()))
        else:
            logger.error(f"Unsupported file format received: {file_extension}")
            raise ValueError(f"Unsupported file format: {file_extension}")

        if pdf_to_process:
             logger.info(f"Extracting content from PDF: {pdf_to_process}")
             return _extract_pdf_content(pdf_to_process)
        else:
             raise Exception("No processable file path determined.")

    except Exception as e:
        logger.error(f"Error processing document {url}: {e}")
        raise Exception(f"Error extracting text from document {url}: {str(e)}")
    finally:
        if converted and pdf_to_process and Path(pdf_to_process).exists():
            try:
                Path(pdf_to_process).unlink()
                logger.info(f"Cleaned up temporary PDF: {pdf_to_process}")
            except OSError as e:
                logger.error(f"Error cleaning up temporary PDF {pdf_to_process}: {e}")