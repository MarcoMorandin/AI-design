# app/services/document_processing.py
import enum
import logging
import json
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF

#from app.utils.file_handler import extract_from_pdf, extract_from_word, extract_from_text, extract_pdf_content
from app.core.config import settings
import requests
import os
import subprocess
from sklearn.metrics.pairwise import cosine_similarity

from transformers import AutoModel, AutoTokenizer
import torch

model_name = "sentence-transformers/all-MiniLM-L6-v2"
model = AutoModel.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

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
        """
        elif file_extension in [".docx", ".doc"]:
            return extract_from_word(file_name)
        elif file_extension in [".txt", ".md"]:
            return extract_from_text(file_name)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        """
    except Exception as e:
        raise Exception(f"Error extracting text from document: {str(e)}")

def extract_pdf_content(file_path: str) -> str:
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
    str_file_path=str(file_path)
    with open(str_file_path, 'rb') as f:
        files = {'file': (str_file_path, f, 'application/pdf')}
        response = requests.post(settings.NOUGAT_URL, files=files)
    print(response.json())
    with open('test_ocr.mmd', 'w') as md_file:
        md_file.write(response.text)
    return response.text
    """
    except FileNotFoundError:
        print(f"Errore: Il file non è stato trovato al percorso specificato: {file_path}")
    except requests.exceptions.RequestException as e:
        print(f"Errore durante l'invio della richiesta: {e}")
    except Exception as e:
        print(f"Si è verificato un errore generico: {e}")
    """

def chunk_document_cosine(text:str, images_caption)->List[str]:
    # reverse order otherwise the char_offset increse after inserting the caption
    for img_caption in images_caption[::-1]:
        text=_insert_img_caption(text, img_caption)

    chunks=get_initial_chunks(text)
    if len(chunks)>=1:
        distances, chunks=_cosine_distance(chunks)
        indices_above_trheshold=_indices_above_treshold_distance(distances)
        chunks=_group_chunks(indices_above_trheshold, chunks)
        chunks=_remove_artifacts(chunks)

def _insert_img_caption(text, img_caption):
    temp_text = [text[:img_caption['char_offset']], img_caption['img_caption'], text[img_caption['char_offset']:]]
    return ''.join(temp_text)

def _remove_artifacts(chunks):
    # remove artifacts
    for sentence in chunks:
        # Remove index and sentence field in the list of dictionary
        sentence.pop('index', None)
        sentence.pop('sentence')
    return chunks



def get_initial_chunks(text:str):
    chunks=chunk_document(text)
    chunks = [{'sentence': x, 'index' : i} for i, x in enumerate(chunks)]
    # the second argument indicates the number of sentences to combine before and after the current sentence
    chunks = _combine_sentences(chunks, 1)
    # emnedding
    chunks=_do_embedding(chunks)
    return chunks

def _group_chunks(indices, sentences):
    # initialize the start index
    start_index = 0
    # create a list to hold the grouped sentences
    final_chunks = []
    # iterate through the breakpoints to slice the sentences
    for index in indices:
        # the end index is the current breakpoint
        end_index = index
        # slice the sentence_dicts from the current start index to the end index
        group = sentences[start_index:end_index + 1]
        combined_text = ' '.join([repr(d['sentence']) for d in group])
        final_chunks.extend(_check_len([combined_text]))
        start_index = index + 1
    # the last group, if any sentences remain
    if start_index < len(sentences):
        combined_text = ' '.join([repr(d['sentence']) for d in sentences[start_index:]])
        final_chunks.extend(_check_len([combined_text]))
    return final_chunks

def _check_len(chunk):
    # chek if the amount of token id above the limit
    if len(chunk)*0.75>1024:
        docs_split=chunk_document(chunk)
        # get new embeddings for the new chunks
        return _get_new_chunk(len(docs_split), docs_split)
    else:
        #st.write("Sotto i 1024")
        return _get_new_chunk(1, chunk)

def _get_new_chunk(leng, chunks):
    splitted_chunks = []
    # get strings from documents
    string_text = [chunks for i in range(leng)]
    chunks_edit = [{'sentence': x, 'index' : i} for i, x in enumerate(string_text)]
    chunks_edit = [{'sentence': f"{x['sentence']}", 'index': x['index']} for x in chunks_edit]
    # get sentence and combined_sentence
    for i in range(len(chunks_edit)):
        combined_sentence = chunks_edit[i]['sentence']
        chunks_edit[i]['section'] = combined_sentence
    # get new embeddings for the new chunks
    chunks_edit=_do_embedding(chunks_edit)
    # add the new chunks to the list
    splitted_chunks.extend(chunks_edit)
    return splitted_chunks


def _indices_above_treshold_distance(distances, distance=0.95):
    # identify the outlier
    # higher distance --> less chunks
    # lower distance --> more chunks
    # Indexes of the chunks with cosine distance above treshold
    indices_above_thresh=[]
    for i, x in enumerate(distances):
        if (1-x)<(distance):
            indices_above_thresh.append(i)
    return indices_above_thresh

def _cosine_distance(chunks):
    distances = []
    for i in range(len(chunks) - 1):
        embedding_current = chunks[i]['embedding']
        embedding_next = chunks[i + 1]['embedding']
        # calculate cosine similarity
        similarity = cosine_similarity([embedding_current], [embedding_next])[0][0]
        # convert to cosine distance
        distance = 1 - similarity
        # append cosine distance to the list
        distances.append(distance)
        # store distance in the dictionary
        chunks[i]['distance_to_next'] = distance
    return distances, chunks


def _do_embedding(chunks):
    embeddings = []
    for chunk in chunks:
        inputs = tokenizer(chunk, return_tensors="pt")
        outputs = model(**inputs)
        embeddings.append((outputs.last_hidden_state[:, 0, :]).detach().numpy()[0])  # Prendi l'embedding della prima parola (CLS)
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
    return chunks

#buffer size: number of sentence before and after the current one to be joined
def _combine_sentences(chunks:str, buffer_size):
    for i in range(len(chunks)):
        # create a string for the joined sentences
        combined_sentence = ''
        # add sentences before the current one, based on the buffer size.
        for j in range(i - buffer_size, i):
            # check if the index j is not negative (avoid problem for the first sentence)
            if j >= 0:
                combined_sentence += chunks[j]['sentence'] + ' '
        # add the current sentence
        combined_sentence += chunks[i]['sentence']

        # add sentences after the current one, based on the buffer size
        for j in range(i + 1, i + 1 + buffer_size):
            # check if the index j is within the range of the sentences list
            if j < len(chunks):
                combined_sentence += ' ' + chunks[j]['sentence']
        # store the combined sentence in the current sentence dict
        chunks[i]['section'] = combined_sentence
    return chunks

def chunk_document(text: str) -> List[str]:
    """
    Suddivide il testo del documento in chunk gestibili per l'elaborazione,
    introducendo anche un overlapping tra i chunk in base al valore impostato in settings.OVERLAP.
    
    Args:
        text: Testo completo del documento.
    
    Returns:
        Una lista di chunk di testo
    """
    chunks = []
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


def get_image_info(file_name: str) -> List[Dict[int, str]]:
    image_positions  = []
        
    try:
        # Open PDF
        doc = fitz.open(Path(file_name))

        
        for page_num, page in enumerate(doc):
            # Ottieni blocchi di testo con informazioni di formattazione
            blocks = page.get_text("dict")["blocks"]
            #sort by readi
            sorted_blocks = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
            char_count=0
            images_in_page = [] #image info
            
            for block in sorted_blocks:
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        # concat text
                        line_text = "".join(span["text"] for span in line["spans"])
                        char_count += len(line_text)
                
                elif block["type"] == 1:  # image block
                    xref = block.get("image") or block.get("xref")
                    if xref:
                        # Estrazione dell'immagine dal PDF
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_caption=_generate_caption_with_blip(Image.open(io.BytesIO(image_bytes)))
                    images_in_page.append({
                        "char_offset": char_count,
                        "img_caption": image_caption,
                    })
            
            image_positions.append(images_in_page)

        doc.close()
        return image_positions
        
    except Exception as e:
        logger.error(f"Errore nell'estrazione del testo: {e}")
        return {}

def _generate_caption_with_blip(byte_image):
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