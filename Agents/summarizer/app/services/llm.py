# app/services/llm.py
import logging
from typing import Optional
import httpx

from app.core.config import settings
from app.utils import prompts
from typing import List
from app.services.document_processing import extract_markdown


logger = logging.getLogger(__name__)

async def call_ollama(prompt:str, model_str=settings.OLLAMA_MODEL):
    """Sends a prompt to the Ollama API using httpx and returns the response."""
    data = {"model": model_str, "prompt": prompt, "stream": False}
    timeout = httpx.Timeout(settings.OLLAMA_TIMEOUT) # Use configured timeout
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"Calling Ollama model {model_str}. Prompt length: {len(prompt)}")
            response = await client.post(settings.OLLAMA_API_URL, json=data)
            response.raise_for_status()
            result = response.json()
            response_text = result.get('response')
            if not response_text:
                logger.error(f"Ollama response missing 'response' field. Full response: {result}")
                raise ValueError("Ollama response did not contain 'response' field.")
            logger.info(f"Ollama call successful. Response length: {len(response_text)}")
            return response_text
    except httpx.HTTPStatusError as e:
        error_detail = f"HTTP Error: {e.response.status_code} - {e.response.text}"
        logger.error(f"Error calling Ollama API: {error_detail}", exc_info=True)
        raise ConnectionError(f"Ollama API returned status {e.response.status_code}.") from e
    except httpx.RequestError as e:
        error_detail = f"Connection/Request Error: {e}"
        logger.error(f"Error calling Ollama API: {error_detail}", exc_info=True)
        raise ConnectionError(f"Could not connect to Ollama API at {settings.OLLAMA_API_URL}.") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred during Ollama call: {type(e).__name__} - {str(e)}", exc_info=True)
        raise RuntimeError(f"An unexpected error occurred during Ollama API call: {str(e)}") from e

async def generate_final_summary(chunks: List[str]) -> List[str]:
    """
    Process each text chunk to extract key information.

    Args:
        chunks: List of document chunks.

    Returns:
        A list of analysis results for each chunk.
    """
    try:
        chunk_summaries=[]
        for i, chunk in enumerate(chunks):
            prompt =prompts.generate_chunk_summary_prompt(chunk)
            summary = await call_ollama(prompt, model_str=settings.OLLAMA_MODEL)
            chunk_summaries.append(summary)
            logger.info(f"Chunk {i + 1} summary generated.")

        concat_summary = "\n\n---\n\n".join(chunk_summaries)
        logger.info("Generating final summary from chunk summaries...")
        if len(chunks) ==1:
            return concat_summary
        final_prompt = prompts.generate_final_summary(concat_summary)
        summary = await call_ollama(final_prompt, model_str=settings.OLLAMA_MODEL)
        
        return summary
    
    except (ConnectionError, ValueError, RuntimeError) as e:
         # Errors from call_ollama or value errors are caught here
         logger.error(f"Essay generation failed: {e}", exc_info=True)
         raise # Re-raise to be handled by the endpoint
    except Exception as e:
        logger.error(f"An unexpected error occurred during essay generation: {e}", exc_info=True)
        raise RuntimeError("An unexpected internal error occurred during essay generation.") from e
    
