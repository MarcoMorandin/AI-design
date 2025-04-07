# app/services/llm.py
import httpx
import json
import logging
from app.core.config import settings
from app.utils import prompts # Import the prompts module

logger = logging.getLogger(__name__)

async def call_ollama(prompt: str, model: str = settings.OLLAMA_MODEL) -> str:
    """Sends a prompt to the Ollama API using httpx and returns the response."""
    data = {"model": model, "prompt": prompt, "stream": False}
    timeout = httpx.Timeout(settings.OLLAMA_TIMEOUT) # Use configured timeout
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"Calling Ollama model {model}. Prompt length: {len(prompt)}")
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
        logger.error(f"An unexpected error occurred during Ollama call: {e}", exc_info=True)
        raise RuntimeError(f"An unexpected error occurred during Ollama API call.") from e


async def generate_essay_from_transcript(transcript: str) -> str:
    """Generates an essay using Ollama based on the transcript."""
    if not transcript:
        logger.warning("Cannot generate essay: No transcript provided.")
        raise ValueError("Transcript is empty.")

    try:
        if len(transcript) <= settings.MAX_CHARS_PER_CHUNK:
            logger.info("Transcript is short. Generating essay directly...")
            prompt = prompts.generate_essay_prompt(transcript)
            essay = await call_ollama(prompt, model=settings.OLLAMA_MODEL)
        else:
            logger.info(f"Transcript is long ({len(transcript)} chars). Using chunking strategy...")
            chunks = []
            start = 0
            while start < len(transcript):
                end = min(start + settings.MAX_CHARS_PER_CHUNK, len(transcript))
                chunks.append(transcript[start:end])
                start += settings.MAX_CHARS_PER_CHUNK - settings.CHUNK_OVERLAP_CHARS
                if end == len(transcript): break

            logger.info(f"Split transcript into {len(chunks)} chunks.")
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i + 1}/{len(chunks)}...")
                summary_prompt = prompts.generate_chunk_summary_prompt(chunk)
                # Consider using a smaller/faster model for summaries if needed
                summary = await call_ollama(summary_prompt, model=settings.OLLAMA_MODEL)
                # call_ollama now raises exceptions on error
                chunk_summaries.append(summary)
                logger.info(f"Chunk {i + 1} summary generated.")

            concatenated_summaries = "\n\n---\n\n".join(chunk_summaries)
            logger.info("Generating final essay from chunk summaries...")
            final_prompt = prompts.generate_final_essay_prompt(concatenated_summaries)
            essay = await call_ollama(final_prompt, model=settings.OLLAMA_MODEL)
            # call_ollama raises exceptions on error

        logger.info("Essay generation completed successfully.")
        return essay

    except (ConnectionError, ValueError, RuntimeError) as e:
         # Errors from call_ollama or value errors are caught here
         logger.error(f"Essay generation failed: {e}", exc_info=True)
         raise # Re-raise to be handled by the endpoint
    except Exception as e:
        logger.error(f"An unexpected error occurred during essay generation: {e}", exc_info=True)
        raise RuntimeError("An unexpected internal error occurred during essay generation.") from e