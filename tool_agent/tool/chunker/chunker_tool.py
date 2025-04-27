from ..sumarizer.chunker_types.cosine_chuncker import chunk_document_cosine
from ..sumarizer.chunker_types.standardar_chuncker import chunk_document



def get_chunks(text:str, chunker_type:str)->List[str]:
    """
    Splits the input text into chunks using the specified chunker type.
    "standardar" uses a simple algorithm that splits the text into chunks of a fixed size.
    "cosine" uses a more advanced algorithm that splits the text into chunks that are similar to each other.

    Args:
        text (str): The input text to be chunked.
        chunker_type (str): The type of chunking algorithm to use. 
            Supported values are "standardar" and "cosine".

    Returns:
        List[str]: A list of text chunks.

    Raises:
        ValueError: If an invalid chunker type is provided.
    """
    if chunker_type == "standardar":
        return chunk_document(text)
    elif chunker_type == "cosine":
        return chunk_document_cosine(text)
    else:
        raise ValueError("Invalid chunker type: " + chunker_type)

