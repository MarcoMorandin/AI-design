import os

from ....services.PowerOcr.PdfProcessor.PdfTranscriptionToolGemini import (
    PdfTranscriptionToolGemini,
)

from ....services.PowerOcr.VideoProcessor.VideoTranscriptionTool import (
    transcribe_video,
)

from dotenv import load_dotenv

load_dotenv()


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
        api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    return processor.process(pdf_path)


def getTextFromVideo(video_path, language="en"):
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
        "output_format": "vtt",
        "language": language,
        "timestamp": True,
        "api_url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "model": "whisper-large-v3",
        "api_key": os.environ.get("GROQ_API_KEY"),
    }
    return transcribe_video(test_params)
