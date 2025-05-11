from typing import List
from ..core.config import settings

def chunk_document(text: str, max_length=settings.MAX_LENGTH_PER_CHUNK) -> List[str]:
    """
    Suddivide il testo del documento in chunk gestibili per l'elaborazione,
    introducendo anche un overlapping tra i chunk in base al valore impostato in settings.OVERLAP.
    
    Args:
        text: Testo completo del documento.
    
    Returns:
        Una lista di chunk di testo
    """
    chunks = []
    if len(text) < max_length:
        chunks.append(text)
        return chunks
    start=0
    while start < len(text):
        end = min(start + max_length, len(text))
        chunks.append(text[start:end])
        start += max_length - settings.OVERLAPP_CHUNK
        if end==len(text): break
    return chunks
