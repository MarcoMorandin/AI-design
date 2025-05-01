from typing import Dict, Any
import logging
import json

from .utils.exceptions import ProcessingError
from .utils.SystemPrompt import SYSTEM_PROMPT

from requests.exceptions import RequestException
from .PdfTranscriptionTool import PdfTranscriptionTool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PdfTranscriptionToolGemini(PdfTranscriptionTool):
    """Implementation for Google's Gemini API including Gemini 2.0 Flash."""

    def __init__(
        self,
        api_endpoint: str,
        model_name: str,
        api_key: str,
    ):
        super().__init__(api_endpoint, model_name, api_key)

    def _prepare_api_payload(
        self, mime_type: str, base64_pdf_data: str
    ) -> Dict[str, Any]:
        """Custom payload preparation for Gemini API."""
        user_prompt_text = (
            "Please process the entire PDF document provided according to the detailed "
            "instructions in the system prompt (the first text part). Extract all content "
            "and structure from the beginning to the end of the document."
        )

        return {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},  # System prompt first
                        {"text": user_prompt_text},  # Then the user prompt
                        {  # Then the PDF file data
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_pdf_data,
                            }
                        },
                    ]
                }
            ],
            # Add generation configuration
            "generationConfig": {
                "temperature": 0.1,  # Lower temperature for factual extraction
                "topK": 32,
                "topP": 1.0,
                "maxOutputTokens": 8192,
            },
        }

    def _call_llm_api_with_pdf(self, mime_type: str, base64_pdf_data: str) -> str:
        """
        Override to handle Gemini's specific API requirements (API key as query param).

        :param mime_type: The mime type of the file.
        :param base64_pdf_data: Raw Base64 encoded PDF string.
        :return: The processed text from the LLM.
        """
        # Prepare the payload
        payload = self._prepare_api_payload(mime_type, base64_pdf_data)

        # Construct the API URL with the API key as query parameter
        api_url = (
            f"{self.api_endpoint}{self.model_name}:generateContent?key={self.api_key}"
        )

        logger.debug(f"Sending request to Gemini API. URL: {api_url.split('?')[0]}...")

        try:
            response = self.session.post(
                api_url,
                json=payload,
                timeout=super().DEFAULT_API_TIMEOUT,
            )

            # Check response status
            if not response.ok:
                error_details = "N/A"
                try:
                    error_data = response.json()
                    error_details = error_data.get("error", {}).get(
                        "message", response.text[:500]
                    )
                except json.JSONDecodeError:
                    error_details = response.text[:500]

                logger.error(
                    f"Gemini API request failed. Status: {response.status_code}. Details: {error_details}"
                )
                response.raise_for_status()

            # Parse the response
            data = response.json()

            # Check for errors
            if "error" in data:
                error_msg = data.get("error", {}).get(
                    "message", "Unknown Gemini API error"
                )
                logger.error(
                    f"Gemini API returned an error in the response body: {error_msg}"
                )
                raise ProcessingError(f"Gemini API returned an error: {error_msg}")

            # Check for content blocking
            if "candidates" not in data or not data["candidates"]:
                feedback = data.get("promptFeedback", {})
                block_reason = feedback.get("blockReason", "Unknown")

                finish_reason = "N/A"
                if data.get("candidates") and data["candidates"][0].get("finishReason"):
                    finish_reason = data["candidates"][0]["finishReason"]

                logger.warning(
                    f"Gemini API response has no candidates or was stopped. Finish Reason: {finish_reason}. Block Reason: {block_reason}."
                )

                if finish_reason == "MAX_TOKENS":
                    logger.error(
                        "Extraction stopped because the maximum output token limit was reached."
                    )
                    try:
                        partial_content_part = data["candidates"][0]["content"][
                            "parts"
                        ][0]
                        if "text" in partial_content_part:
                            logger.warning(
                                "Returning partial result due to MAX_TOKENS limit."
                            )
                            return (
                                partial_content_part["text"].strip()
                                + "\n\n[WARNING: Output truncated due to maximum token limit]"
                            )
                    except (KeyError, IndexError, TypeError):
                        pass

                raise ProcessingError(
                    f"Gemini API call failed, content blocked, or stopped prematurely. Finish Reason: {finish_reason}, Block Reason: {block_reason}"
                )

            # Extract content
            try:
                content_part = data["candidates"][0]["content"]["parts"][0]
                if "text" in content_part:
                    content = content_part["text"]
                else:
                    logger.warning(
                        f"First part of Gemini response is not text: {content_part}"
                    )
                    raise ProcessingError(
                        "Expected text content from Gemini response, but got different part type."
                    )

                if not isinstance(content, str):
                    raise TypeError(
                        f"Expected string content from Gemini response part, got {type(content)}"
                    )

            except (KeyError, IndexError, TypeError) as e:
                response_preview = json.dumps(data, indent=2)[:1000]
                logger.error(
                    f"Failed to parse expected content from Gemini API response: {e}. Response structure:\n{response_preview}...",
                    exc_info=True,
                )
                raise ProcessingError(
                    f"Unexpected Gemini API response format or error parsing content: {e}"
                ) from e

            # Check finish reason
            finish_reason = data["candidates"][0].get("finishReason", "UNKNOWN")
            if finish_reason != "STOP":
                logger.warning(
                    f"Gemini response finished with reason '{finish_reason}' instead of 'STOP'. Output might be incomplete."
                )
                if finish_reason == "MAX_TOKENS":
                    content += "\n\n[WARNING: Output may be truncated due to maximum token limit]"

            logger.info("Successfully received and parsed Gemini API response.")
            return content.strip()

        except RequestException as e:
            logger.error(f"Gemini API request failed: {e}", exc_info=True)
            response_text = (
                e.response.text[:500]
                if hasattr(e, "response") and e.response is not None
                else "N/A"
            )
            raise ProcessingError(
                f"Gemini API request failed: {e}. Response: {response_text}"
            ) from e
        except ProcessingError as e:
            raise e
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during Gemini API call/processing: {e}",
                exc_info=True,
            )
            raise ProcessingError(
                f"Unexpected error during Gemini API call/processing: {e}"
            ) from e
