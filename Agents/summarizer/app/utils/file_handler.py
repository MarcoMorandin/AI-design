
import fitz  # PyMuPDF
import camelot
import pdfplumber
from docx import Document
from typing import Dict, Any
import logging
import zipfile  # Importato per estrarre i file da un DOCX (che è un file ZIP)
from pathlib import Path
from app.core.config import settings
from typing import List, Tuple, Union
import easyocr
import certifi

reader = easyocr.Reader(['en', 'it'])
OCR_AVAILABLE = True

import uuid
from pathlib import Path
import httpx
from fastapi import HTTPException
# Ensure that your settings, logger, and any cleanup utility functions (like cleanup_files) are properly imported.
# Example:
# from your_project import settings, logger, cleanup_files
logger = logging.getLogger(__name__)


def cleanup_files(*file_paths: Union[Path, str, None]):
    """Safely removes files, ignoring errors if files don't exist."""
    for file_path in file_paths:
        if file_path:
            path = Path(file_path) # Ensure it's a Path object
            if path.exists() and path.is_file(): # Check if it exists and is a file
                try:
                    path.unlink() # Use Path.unlink()
                    logger.info(f"Cleaned up temporary file: {path}")
                except OSError as e:
                    logger.error(f"Error cleaning up file {path}: {e}")
            # Optionally log if file not found, but usually cleanup shouldn't error if file is missing
            # else:
            #     logger.warning(f"Cleanup requested but file not found or not a file: {path}")
            

async def download_document_from_url(pdf_url: str) -> Path:
    """Downloads a PDF from a URL to a temporary file."""
    request_id = uuid.uuid4()
    # Check for a .pdf extension; default to .pdf if not found or if the extension isn't valid.
    suffix = Path(pdf_url).suffix.lower() if Path(pdf_url).suffix.lower() == ".pdf" else ".pdf"
    
    temp_file_path = settings.TEMP_DIR / f"{request_id}_downloaded{suffix}"
    logger.info(f"Attempting to download document from {pdf_url} to {temp_file_path}")

    download_timeout = httpx.Timeout(settings.DOWNLOAD_TIMEOUT, connect=settings.DOWNLOAD_TIMEOUT)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

    try:
        async with httpx.AsyncClient(timeout=download_timeout, limits=limits, follow_redirects=True, verify=certifi.where()) as client:
            async with client.stream("GET", pdf_url) as response:
                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()

                # Optional: Check Content-Type to ensure it's a PDF
                content_type = response.headers.get("content-type", "").lower()
                # Use a list of allowed PDF MIME types. This could be defined in your settings.
                #allowed_pdf_types = getattr(settings, "ALLOWED_PDF_CONTENT_TYPES", ["application/pdf"])
                if settings.ALLOWED_DOCUMENT_CONTENT_TYPES and not any(allowed_type in content_type for allowed_type in settings.ALLOWED_DOCUMENT_CONTENT_TYPES):
                    # Allow a generic stream (e.g., application/octet-stream) as a fallback.
                    if content_type != "application/octet-stream":
                        logger.warning(f"Disallowed content-type '{content_type}' for URL {pdf_url}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported content type: {content_type}. Allowed types: {allowed_pdf_types}"
                        )
                    else:
                        logger.warning(f"Generic content-type '{content_type}', proceeding with download for URL {pdf_url}")

                # Optional: Check Content-Length for file size limits.
                content_length = response.headers.get("content-length")
                max_size_bytes = settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024  # Convert MB to bytes
                if content_length and int(content_length) > max_size_bytes:
                    logger.warning(f"Content-Length {content_length} exceeds limit of {max_size_bytes} bytes for URL {pdf_url}")
                    raise HTTPException(
                        status_code=413,  # Payload Too Large
                        detail=f"PDF file size ({int(content_length) / 1024 / 1024:.1f} MB) exceeds limit of {settings.MAX_DOWNLOAD_SIZE_MB} MB."
                    )

                # Stream the download to a file.
                downloaded_size = 0
                with open(temp_file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        downloaded_size += len(chunk)
                        # If no Content-Length header, check the file size on the fly.
                        if not content_length and downloaded_size > max_size_bytes:
                            f.close()  # Ensure the file is closed before cleaning up.
                            cleanup_files(temp_file_path)  # Clean up the partial file.
                            logger.warning(f"Download exceeded size limit ({max_size_bytes} bytes) during streaming for URL {pdf_url}")
                            raise HTTPException(
                                status_code=413,
                                detail=f"PDF file size exceeds limit of {settings.MAX_DOWNLOAD_SIZE_MB} MB (detected during download)."
                            )
                        f.write(chunk)

        logger.info(f"Successfully downloaded PDF from {pdf_url} ({downloaded_size / 1024 / 1024:.2f} MB) to {temp_file_path}")
        return temp_file_path

    except httpx.HTTPError as http_err:
        logger.error(f"HTTP error occurred during PDF download: {http_err}")
        raise HTTPException(status_code=400, detail=str(http_err))
    except Exception as err:
        logger.error(f"Unexpected error occurred during PDF download: {err}")
        cleanup_files(temp_file_path) # Attempt cleanup on unexpected errors
        raise HTTPException(status_code=500, detail="An unexpected error occurred while downloading the PDF.")

def _extract_text_with_format(file_name: str) -> Dict[str, List[Tuple[str, Any]]]:
    formatted_text = {}
        
    try:
        # Open PDF
        doc = fitz.open(Path(file_name))

        
        for page_num, page in enumerate(doc):
            # Ottieni blocchi di testo con informazioni di formattazione
            blocks = page.get_text("dict")["blocks"]
            page_text = []
            
            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        line_text = ""
                        line_formats = []
                        
                        for span in line["spans"]:
                            line_text += span["text"]
                            # Salva informazioni sul font e dimensione
                            line_formats.append({
                                "font": span["font"],
                                "size": span["size"],
                                "color": span["color"]
                            })
                        
                        page_text.append((line_text, line_formats))
            if OCR_AVAILABLE:
                image_texts = []
                
                # Prima raccogliamo tutto il testo dalle immagini nella pagina
                for img_index, img in enumerate(page.get_images()):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    try:
                        result = reader.readtext(image_bytes)
                        for (bbox, text, prob) in result:
                            if prob > 0.25:  # Probabilità minima per considerare il testo valido
                                # Salva il testo con la sua posizione approssimativa
                                image_texts.append({
                                    "text": text,
                                    "probability": prob,
                                    "bbox": bbox,
                                    "img_index": img_index
                                })
                    except Exception as e:
                        logger.error(f"Errore OCR nell'immagine {img_index} pagina {page_num+1}: {e}")
                
                # Se abbiamo trovato testo nelle immagini, lo integriamo come parte del testo della pagina
                if image_texts:
                    # Ordinamento per probabilità per avere prima i testi più affidabili
                    image_texts.sort(key=lambda x: x["probability"], reverse=True)
                    
                    # Creiamo una entry di testo normale per ogni testo trovato nelle immagini
                    for img_text in image_texts:
                        text = img_text["text"]
                        page_text.append((
                            text,
                            [{"font": "OCR", "size": 10, "color": 0}]
                        ))

            formatted_text[f"Page_{page_num}"] = page_text
            
        doc.close()
        return formatted_text
        
    except Exception as e:
        logger.error(f"Errore nell'estrazione del testo: {e}")
        return {}

def _extract_tables(pdf_path: str) -> Dict[int, List[Any]]:
        """
        Estrae tabelle da un PDF usando camelot-py.
        
        Args:
            pdf_path: Percorso del file PDF
            
        Returns:
            Dizionario con indice pagina e lista di tabelle
        """
        tables_by_page = {}
        
        try:
            # Usando camelot per tabelle con bordi
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            # Anche tabelle senza bordi definiti
            stream_tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            # Combina risultati
            for table in tables:
                page = table.page
                if page not in tables_by_page:
                    tables_by_page[page] = []
                tables_by_page[page].append(table)
                
            for table in stream_tables:
                page = table.page
                if page not in tables_by_page:
                    tables_by_page[page] = []
                # Aggiungi solo se ha una buona valutazione di accuratezza
                if table.accuracy > 80:
                    tables_by_page[page].append(table)
            
            return tables_by_page
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione delle tabelle: {e}")
            return {}
def _table_to_markdown(table) -> str:
        """
        Converte una tabella in formato markdown.
        
        Args:
            table: Oggetto tabella da convertire
            
        Returns:
            Stringa formattata in markdown
        """
        df = table.df
        markdown = []
        
        # Intestazioni
        headers = '|' + '|'.join(str(col).replace('\n', ' ') for col in df.iloc[0]) + '|'
        markdown.append(headers)
        
        # Separatore
        separator = '|' + '|'.join(['---'] * len(df.columns)) + '|'
        markdown.append(separator)
        
        # Righe
        for i in range(1, len(df)):
            row = '|' + '|'.join(str(cell).replace('\n', ' ') if str(cell) != 'nan' else '' 
                                for cell in df.iloc[i]) + '|'
            markdown.append(row)
            
        return '\n'.join(markdown)

def extract_pdf_content(pdf_path: str) -> str:
    """
    Estrae il contenuto completo di un PDF, combinando testo e tabelle.
    
    Args:
        pdf_path: Percorso del file PDF
        
    Returns:
        Lista di oggetti Document con il contenuto estratto
    """
    #if not Path(pdf_path).exists():
    #    logger.error(f"File non trovato: {pdf_path}")
    #    return []
        
    try:
        #path_file=Path(settings.TEMP_DIR) / f"{pdf_path}"
        # Estrai testo formattato
        logger.info(f"EXTRACTING TEXT")  # Loggin
        text_content = _extract_text_with_format(pdf_path)
        logger.info(f"EXTRACTING TABLES")  # Loggin
        # Estrai tabelle
        tables_content = _extract_tables(pdf_path)
        
        # Documento finale
        doc = fitz.open(pdf_path)
        final_content = []
        
        for page_num in range(len(doc)):
            page_key = f"Page_{page_num}"
            page_content = []
            
            # Aggiungi testo
            if page_key in text_content:
                for line_text, _ in text_content[page_key]:
                    page_content.append(line_text)
            
            # Aggiungi tabelle
            if page_num + 1 in tables_content:  # camelot usa indici basati su 1
                for table in tables_content[page_num + 1]:
                    page_content.append("\n" + _table_to_markdown(table) + "\n")
            
            final_content.append("\n".join(page_content))
        
        doc.close()
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write("\n\n".join(final_content))
        return "\n\n".join(final_content)
        # Crea documento LangChain
        #return [Document(page_content="\n\n".join(final_content))]
        
    except Exception as e:
        logger.error(f"Errore nell'estrazione del contenuto: {e}")
        return []

def extract_from_pdf(file_path: str) -> str:
    """Estrae il testo dai documenti PDF, includendo il testo ottenuto da immagini (se OCR è disponibile)."""
    try:
        doc=fitz.open(file_path)
        #doc = fitz.open(Path(settings.TEMP_DIR) / f"{file_name}")
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
