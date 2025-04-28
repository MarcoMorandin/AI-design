from typing import Dict, Any, Tuple
import requests
import logging
import base64
import os
import json
from .utils.exceptions import ProcessingError
from .utils.SystemPrompt import SYSTEM_PROMPT

from requests.exceptions import RequestException


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PdfTranscriptionTool:
    """
    Extracts structured content from PDF documents by sending the entire PDF
    file to an LLM API via HTTP request.

    Attributes:
        model_name (str): The LLM model identifier.
        api_key (str): The API key for the LLM provider.
        api_endpoint (str): The API endpoint URL.
    """

    DEFAULT_API_TIMEOUT = 300  # Increased timeout for handling large PDF files

    def __init__(
        self,
        api_endpoint: str,
        model_name: str,
        api_key: str,
    ):
        """
        Initializes the PDFNativeLLMExtractor client.

        :param api_endpoint: The API endpoint URL for the chosen LLM provider.
        :param model_name: LLM model identifier.
        :param api_key: LLM provider's API key. Reads from env var if None.

        :raises ValueError: If model name or endpoint is empty.
        :raises ProcessingError: If API key is not found.
        """
        if not model_name:
            raise ValueError("Model name cannot be empty.")
        if not api_endpoint:
            raise ValueError("API endpoint cannot be empty.")
        if not api_key:
            raise ValueError("API key cannot be empty.")

        self.model_name = model_name
        self.api_endpoint = api_endpoint
        self.api_key = api_key

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        logger.info(f"PDFNativeLLMExtractor initialized for model '{self.model_name}'")

    def _read_and_encode_pdf(self, pdf_path: str) -> Tuple[str, str]:
        """
        Reads the PDF file as bytes and encodes it in Base64.

        :param pdf_path: Path to the PDF file.
        :return: Tuple containing (mime_type string ("application/pdf"), raw Base64 encoded PDF string).
        :raises FileNotFoundError: If pdf_path doesn't exist.
        :raises ProcessingError: If the file cannot be read.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        logger.debug(f"Reading and Base64 encoding PDF: '{pdf_path}'")
        try:
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()

            base64_encoded_data = base64.b64encode(pdf_bytes)
            base64_pdf_string = base64_encoded_data.decode("utf-8")
            mime_type = "application/pdf"

            logger.debug(
                f"Successfully read and encoded PDF (mime: {mime_type}, encoded length: {len(base64_pdf_string)})."
            )
            return mime_type, base64_pdf_string

        except IOError as e:
            logger.error(f"Failed to read PDF file '{pdf_path}': {e}", exc_info=True)
            raise ProcessingError(f"Failed to read PDF file '{pdf_path}': {e}") from e
        except Exception as e:
            logger.error(f"Failed to encode PDF file '{pdf_path}': {e}", exc_info=True)
            raise ProcessingError(f"Failed encode PDF file '{pdf_path}': {e}") from e

    def _prepare_api_payload(
        self, mime_type: str, base64_pdf_data: str
    ) -> Dict[str, Any]:
        """
        Prepares the payload for the LLM API request.
        Override this method in subclasses to support different API formats.

        :param mime_type: The mime type of the file.
        :param base64_pdf_data: Raw Base64 encoded PDF string.
        :return: A dictionary containing the prepared payload for the API request.
        """
        # This is a generic example - each LLM provider will require specific formatting
        user_prompt_text = (
            "Please process the entire PDF document provided according to the detailed "
            "instructions in the system prompt. Extract all content "
            "and structure from the beginning to the end of the document."
        )

        # Generic payload structure - customize for specific LLM providers
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt_text},
                        {
                            "type": "image",
                            "format": "base64",
                            "mime_type": mime_type,
                            "data": base64_pdf_data,
                        },
                    ],
                },
            ],
            "temperature": 0.1,  # Lower temperature for factual extraction
            "max_tokens": 8192,  # Adjust based on provider's limits
        }

        return payload

    def _call_llm_api_with_pdf(self, mime_type: str, base64_pdf_data: str) -> str:
        """
        Sends the encoded PDF data and prompt to the LLM API.

        :param mime_type: The mime type of the file ("application/pdf").
        :param base64_pdf_data: Raw Base64 encoded PDF string.
        :return: The processed text content string from the LLM API response.
        :raises ProcessingError: If the API request fails, returns an error, or the response is unexpected.
        """
        # Prepare the payload for the specific LLM provider
        payload = self._prepare_api_payload(mime_type, base64_pdf_data)

        api_url = self.api_endpoint
        headers = {"Authorization": f"Bearer {self.api_key}"}

        logger.debug(f"Sending request to LLM API. URL: {api_url}")

        try:
            response = self.session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=self.DEFAULT_API_TIMEOUT,
            )

            # Check response status before attempting to parse JSON
            if not response.ok:
                error_details = "N/A"
                try:
                    error_data = response.json()
                    error_details = str(error_data)[
                        :500
                    ]  # Use first 500 chars of error data
                except json.JSONDecodeError:
                    error_details = response.text[:500]  # Use raw text if not JSON

                logger.error(
                    f"LLM API request failed. Status: {response.status_code}. Details: {error_details}"
                )

                if (
                    response.status_code == 400
                ):  # Bad Request often indicates payload issues
                    logger.error(
                        "A 400 Bad Request might indicate an issue with the payload size, encoding, or structure."
                    )
                elif response.status_code == 500:  # Internal Server Error
                    logger.error(
                        "A 500 Internal Server Error might indicate a temporary issue on the provider's side."
                    )

                response.raise_for_status()  # Will raise HTTPError

            # Parse response JSON - adapt this section based on your LLM provider's response format
            data = response.json()

            # Generic extraction logic - customize for your LLM provider
            try:
                # Extract text based on common response patterns
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content", "")
                elif "candidates" in data and data["candidates"]:
                    content = (
                        data["candidates"][0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                elif "output" in data:
                    content = data.get("output", {}).get("text", "")
                elif "completion" in data:
                    content = data.get("completion", "")
                elif "response" in data:
                    content = data.get("response", "")
                else:
                    # Fallback to looking for any text field
                    for key in ["text", "content", "result", "answer"]:
                        if key in data:
                            content = data[key]
                            break
                    else:
                        raise KeyError("Could not find content in the response")

                if not isinstance(content, str):
                    raise TypeError(
                        f"Expected string content from LLM response, got {type(content)}"
                    )

            except (KeyError, IndexError, TypeError) as e:
                response_preview = json.dumps(data, indent=2)[:1000]
                logger.error(
                    f"Failed to parse expected content from LLM API response: {e}. Response structure:\n{response_preview}...",
                    exc_info=True,
                )
                raise ProcessingError(
                    f"Unexpected LLM API response format or error parsing content: {e}"
                ) from e

            # Check for truncation indicators
            truncation_indicators = ["MAX_TOKENS", "LENGTH", "token limit", "truncated"]
            if any(indicator in str(data) for indicator in truncation_indicators):
                logger.warning(
                    "LLM response may be truncated due to token limits. Output might be incomplete."
                )
                content += (
                    "\n\n[WARNING: Output may be truncated due to maximum token limit]"
                )

            logger.info("Successfully received and parsed LLM API response.")
            return content.strip()

        except RequestException as e:
            logger.error(f"LLM API request failed: {e}", exc_info=True)
            response_text = (
                e.response.text[:500]
                if hasattr(e, "response") and e.response is not None
                else "N/A"
            )
            raise ProcessingError(
                f"LLM API request failed: {e}. Response: {response_text}"
            ) from e
        except ProcessingError as e:  # Catch ProcessingError explicitly
            raise e
        except Exception as e:  # Catch any other unexpected errors
            logger.error(
                f"An unexpected error occurred during API call/processing: {e}",
                exc_info=True,
            )
            raise ProcessingError(
                f"Unexpected error during API call/processing: {e}"
            ) from e

    def process(self, pdf_path: str) -> str:
        """
        Performs the full PDF processing workflow by sending the entire file to the LLM.

        Reads the PDF, Base64 encodes it, sends it to the LLM API,
        and returns the structured text result.

        :param pdf_path: Path to the PDF file to process.
        :return: A single string containing the combined structured output from the LLM.
        :raises FileNotFoundError: If the pdf_path does not exist.
        :raises ProcessingError: If any step (reading, encoding, API call) fails.
        """
        logger.info(
            f"Starting native PDF processing for '{pdf_path}' using model '{self.model_name}'..."
        )

        try:
            # 1. Read and Encode PDF
            mime_type, base64_pdf_data = self._read_and_encode_pdf(pdf_path)

            # 2. Call LLM API with the PDF data
            processed_text = self._call_llm_api_with_pdf(mime_type, base64_pdf_data)

        except (FileNotFoundError, ProcessingError) as e:
            # Logged in helper methods, re-raise to halt
            logger.error(f"Halting processing due to error: {e}")
            raise e
        except Exception as e:  # Catch any other unexpected error during the process
            logger.error(
                f"Unexpected error during PDF processing workflow: {e}", exc_info=True
            )
            raise ProcessingError(f"Unexpected error during PDF processing: {e}") from e

        logger.info(
            f"Native PDF processing completed for '{pdf_path}'. Final output length: {len(processed_text)} characters."
        )
        return processed_text
