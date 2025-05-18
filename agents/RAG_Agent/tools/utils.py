def chunk_text(text, chunk_size=512, overlap=64):
    """
    Split a text into chunks of specified size with overlap between consecutive chunks.
    
    Args:
        text (str): The input text to be chunked
        chunk_size (int, optional): Size of each chunk in characters. Defaults to 512.
        overlap (int, optional): Number of overlapping characters between chunks. Defaults to 64.
        
    Returns:
        list: List of text chunks
    """
    # Check if the text is shorter than chunk_size
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Calculate end position for current chunk
        end = min(start + chunk_size, len(text))
        
        # Add the chunk to our list
        chunks.append(text[start:end])
        
        # Move the start position for the next chunk, accounting for overlap
        start = end - overlap
        
        # If we've reached the end of the text, break
        if start + overlap >= len(text):
            break
    
    return chunks