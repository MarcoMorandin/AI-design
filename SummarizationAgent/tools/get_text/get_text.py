import os

from .PowerOcr.PdfProcessor.PdfTranscriptionToolGemini import (
    PdfTranscriptionToolGemini,
)

from .PowerOcr.VideoProcessor.VideoTranscriptionTool import (
    transcribe_video,
)

from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


def getTextFromPdf(pdf_path):
    """
    Extracts text from a PDF file.

    Args:
       pdf_path (str): The path to the PDF file.

    Returns:
       str: The extracted text from the PDF file.
    """

    processor = PdfTranscriptionToolGemini(
        api_endpoint="https://generativelanguage.googleapis.com/v1beta/models/",
        model_name="gemini-2.0-flash",
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    try:
        return processor.process(pdf_path)
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")


def getTextFromVideo(video_path, language="it"):
    """
    Extracts text from a video file.

    Args:
       video_path (str): The path to the video file.
       language (str): The language of the video. Default is "en".

    Returns:
       str: The extracted text from the video file.
    """

    test_params = {
        "video_path": video_path,
        "output_format": "plain",
        "language": language,
        "timestamp": False,
        "api_url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "model": "whisper-large-v3-turbo",
        "api_key": os.environ.get("GROQ_API_KEY"),
    }

    try:
        trans = transcribe_video(test_params)

        return trans["transcription"]
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")
