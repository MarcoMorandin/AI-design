import logging
import os
import sys

from PowerOcr.PdfProcessor.PdfTranscriptionToolGemini import (
    PdfTranscriptionToolGemini,
)
from dotenv import load_dotenv

load_dotenv()


API_KEY = os.environ.get("GOOGLE_API_KEY")

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():

    processor = PdfTranscriptionToolGemini(
        api_endpoint="https://generativelanguage.googleapis.com/v1beta/models/",
        model_name="gemini-2.0-flash",
        api_key=API_KEY,
    )

    result = processor.process("./input/test.pdf")

    with open("./output/test-document-result.md", "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Structured output successfully saved")


if __name__ == "__main__":
    # Install the required packages if not already installed (requests)
    main()
