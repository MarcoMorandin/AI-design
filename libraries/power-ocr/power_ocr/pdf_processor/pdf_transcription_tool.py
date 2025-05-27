from typing import Dict, Any, Tuple
import logging
import base64
import os
import json
from openai import OpenAI
from ..utils.exceptions import ProcessingError
from ..utils.system_prompt import PDF_SYSTEM_PROMPT

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PdfTranscriptionTool:
    """
    Extracts structured content from PDF documents by sending the entire PDF
    file to an LLM API via OpenAI-compatible SDK interface.

    Attributes:
        model_name (str): The LLM model identifier.
        api_key (str): The API key for the LLM provider.
        api_base (str): The API base URL.
        client: OpenAI client instance
    """

    DEFAULT_API_TIMEOUT = 300  # Increased timeout for handling large PDF files

    def __init__(
        self,
        api_base: str,
        model_name: str,
        api_key: str,
    ):
        """
        Initializes the PDF transcription tool using OpenAI client.

        :param api_base: The API base URL for the chosen LLM provider.
        :param model_name: LLM model identifier.
        :param api_key: LLM provider's API key.

        :raises ValueError: If model name or endpoint is empty.
        :raises ProcessingError: If API key is not found.
        """
        if not model_name:
            raise ValueError("Model name cannot be empty.")
        if not api_base:
            raise ValueError("API base URL cannot be empty.")
        if not api_key:
            raise ValueError("API key cannot be empty.")

        self.model_name = model_name
        self.api_base = api_base
        self.api_key = api_key

        # Initialize OpenAI client with the provider's base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=self.DEFAULT_API_TIMEOUT,
        )

        logger.info(f"PDF Transcription Tool initialized for model '{self.model_name}'")

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

    def _call_llm_api_with_pdf(self, mime_type: str, base64_pdf_data: str) -> str:
        """
        Sends the encoded PDF data and prompt to the LLM API using OpenAI SDK.

        :param mime_type: The mime type of the file ("application/pdf").
        :param base64_pdf_data: Raw Base64 encoded PDF string.
        :return: The processed text content string from the LLM API response.
        :raises ProcessingError: If the API request fails or the response is unexpected.
        """
        user_prompt_text = (
            "Please process the entire PDF document provided according to the detailed "
            "instructions in the system prompt. Extract all content "
            "and structure from the beginning to the end of the document."
        )

        try:
            logger.debug(
                f"Sending request to {self.api_base} with model {self.model_name}"
            )

            # Create the message with system prompt and user content
            messages = [
                {"role": "system", "content": PDF_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_pdf_data}"
                            },
                        },
                    ],
                },
            ]

            # Call the API using the OpenAI SDK
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=8192,
            )

            # Extract content from the response
            if not response.choices or len(response.choices) == 0:
                raise ProcessingError("API response contained no choices")

            content = response.choices[0].message.content

            if not content:
                raise ProcessingError("API response contained empty content")

            logger.info("Successfully received and parsed LLM API response.")
            return content.strip()

        except Exception as e:
            logger.error(f"Error during API call/processing: {str(e)}", exc_info=True)
            raise ProcessingError(f"Error during API call/processing: {str(e)}") from e

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
            f"Starting PDF processing for '{pdf_path}' using model '{self.model_name}'..."
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
            f"PDF processing completed for '{pdf_path}'. Final output length: {len(processed_text)} characters."
        )
        return processed_text
