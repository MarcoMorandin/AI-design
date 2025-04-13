from typing import List
from app.core.config import settings

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
