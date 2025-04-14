
from pathlib import Path
import io
import logging
from typing import List, Dict
import fitz  # PyMuPDF
from PIL import Image
import torch
from torch.cuda.amp import autocast
from transformers import BlipProcessor, BlipForConditionalGeneration

def get_image_info(file_name: str) -> List[List[Dict]]:
    """
    Extract images from PDF and their positions in terms of character count.
    
    Args:
        file_name: Path to the PDF file
        
    Returns:
        List of lists, where each inner list contains dictionaries with image information for each page
    """
    image_positions = []
        
    try:
        # Open PDF
        doc = fitz.open(Path(file_name))
        print(f"Number of pages: {len(doc)}")
        
        for page_num, page in enumerate(doc):
            # Get text blocks with formatting information
            blocks = page.get_text("dict")["blocks"]
            # Sort by reading order
            sorted_blocks = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
            char_count = 0
            images_in_page = []  # image info for this page
            
            for block in sorted_blocks:
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        # Concatenate text from spans
                        line_text = "".join(span["text"] for span in line["spans"])
                        char_count += len(line_text)
                
                elif block["type"] == 1:  # image block
                    # Get image reference number
                    xref = block.get("image", 0)
                    if not xref:
                        xref = block.get("xref", 0)
                    if xref and isinstance(xref, int):  # Ensure xref is an integer
                        try:
                            # Extract image from PDF
                            base_image = doc.extract_image(xref)
                            print(f"Base image: {base_image}")
                            if base_image and "image" in base_image:
                                image_bytes = base_image["image"]
                                pil_image = Image.open(io.BytesIO(image_bytes))
                                image_caption = _generate_caption_with_blip(pil_image)
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
        logger.error(f"Error extracting text from document: {str(e)}")
        raise Exception(f"Error extracting text from document: {str(e)}")


def _generate_caption_with_blip(byte_image):
    print("generate_caption")
    try:
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


if __name__ == "__main__":
    model_name = "Salesforce/blip-image-captioning-base"
    processor = BlipProcessor.from_pretrained(model_name)
    model = BlipForConditionalGeneration.from_pretrained(model_name)

    result=get_image_info("test.pdf")
    print()