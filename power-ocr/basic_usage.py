#!/usr/bin/env python3
"""
Power OCR - Example Usage Script

This script demonstrates how to use both the PDF and video transcription
functionality from the power-ocr library.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the power-ocr library

from power_ocr import PdfTranscriptionTool, transcribe_video


def process_pdf(pdf_path, output_path):
    """Process a PDF file using the PdfTranscriptionTool."""
    print(f"Processing PDF: {pdf_path}")

    # Initialize the transcription tool
    tool = PdfTranscriptionTool(
        api_base=os.environ.get("PDF_OCR_API_ENDPOINT"),
        model_name=os.environ.get("PDF_OCR_MODEL_NAME"),
        api_key=os.environ.get("PDF_OCR_API_KEY"),
    )

    # Process the PDF
    result = tool.process(pdf_path)

    # Save the result
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"PDF transcription saved to: {output_path}")


def process_video(video_path, output_path):
    """Process a video file using the transcribe_video function."""
    print(f"Processing video: {video_path}")

    # Prepare parameters
    params = {
        "video_path": video_path,
        "api_base": os.environ.get("VIDEO_OCR_API_URL"),
        "api_key": os.environ.get("VIDEO_OCR_API_KEY"),
        "model": os.environ.get("VIDEO_OCR_MODEL_NAME", "whisper-large-v3"),
    }

    # Process the video
    result = transcribe_video(params)

    # Check for errors
    if result["status"] == "error":
        print(f"Error: {result['error']}")
        return

    # Save the transcription
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["transcription"])

    print(f"Video transcription saved to: {output_path}")


def main():
    # Process PDF
    process_pdf("test.pdf", "test_pdf.md")

    # Process video
    process_video("test.mp4", "test_video.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
