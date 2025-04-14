
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import requests
from typing import List, Dict
import fitz
from pathlib import Path


def get_image_info(file_name: str) -> List[Dict[int, str]]:

    image_positions = []
        
    try:
        # Open PDF
        doc = fitz.open(Path(file_name))
        print(len(doc))
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
        raise Exception(f"Error extracting text from document: {str(e)}")
        #logger.error(f"Errore nell'estrazione del testo: {e}")


def _generate_caption_with_blip(byte_image):

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
    # Open the PDF file in binary mode
    #file_name=os.path.splitext(file_path)[0]+os.path.splitext(file_path)[1]
    #print("File_name_weith_estension", file_name)
    #with open(file_path, 'rb') as f:
    #files = {'file': (file_name, f, 'application/pdf')}
    # Send the POST request
    try:
        str_file_path=str(file_path)
        with open(str_file_path, 'rb') as f:
            files = {'file': (str_file_path, f, 'application/pdf')}
            response = requests.post("http://127.0.0.1:8503/predict/", files=files)
            # reverse order otherwise the char_offset increse after inserting the caption
        #for img_caption in images_caption[::-1]:
        #    response=_insert_img_caption(response.text, img_caption)
        print(response.json())
        with open('test_ocr.mmd', 'w') as md_file:
            md_file.write(response.json())
        return response.text
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")

if __name__ == "__main__":
    model_name = "Salesforce/blip-image-captioning-base"
    processor = BlipProcessor.from_pretrained(model_name)
    model = BlipForConditionalGeneration.from_pretrained(model_name)

    result=get_image_info("test.pdf")
    print()