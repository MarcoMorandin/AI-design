# Power OCR

AI-powered transcription tools for PDF and video files. This library provides Python functions and command-line utilities to transcribe PDFs and videos using AI services via OpenAI-compatible APIs.

## Features

- **PDF Processing:** Extract structured content from PDF files with proper formatting
- **Video Transcription:** Generate text transcripts from video files with automatic language detection
- **Command-line Tools:** Ready-to-use CLI utilities for both PDF and video processing
- **Python API:** Easy-to-use Python functions for integration into your projects

## Installation

```bash
pip install power-ocr
```

Or install from the repository:

```bash
git clone https://github.com/yourusername/power-ocr.git
cd power-ocr
pip install -e .
```

## Prerequisites

- Python 3.8 or higher
- FFmpeg (required for video processing)
- API key for OpenAI or compatible service

## Setup

1. Install FFmpeg if not already installed (required for video processing):
   - MacOS: `brew install ffmpeg`
   - Ubuntu/Debian: `apt-get install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/) or use `choco install ffmpeg`

2. Set up environment variables (or provide via CLI arguments):

```bash
# PDF processing
export PDF_OCR_API_ENDPOINT="https://api.openai.com/v1"
export PDF_OCR_MODEL_NAME="gpt-4-vision-preview"
export PDF_OCR_API_KEY="your-api-key"

# Video processing
export VIDEO_OCR_API_URL="https://api.openai.com/v1"
export VIDEO_OCR_MODEL_NAME="whisper-large-v3"
export VIDEO_OCR_API_KEY="your-api-key"
```

Or create a `.env` file in your project directory with the above variables.

## Command-line Usage

### PDF Transcription

```bash
# Basic usage
pdf-transcribe document.pdf

# With custom options
pdf-transcribe document.pdf --output result.md --api-base https://api.openai.com/v1 --model gpt-4-vision-preview --api-key your-api-key
```

### Video Transcription

```bash
# Basic usage
video-transcribe video.mp4

# With custom options
video-transcribe video.mp4 --output transcript.md --api-base https://api.openai.com/v1 --model whisper-large-v3 --api-key your-api-key --language en
```

## Python API Usage

### PDF Processing

```python
from power_ocr import PdfTranscriptionTool
import os

# Initialize the tool
tool = PdfTranscriptionTool(
    api_base=os.environ.get("PDF_OCR_API_ENDPOINT"),
    model_name=os.environ.get("PDF_OCR_MODEL_NAME"),
    api_key=os.environ.get("PDF_OCR_API_KEY"),
)

# Process PDF and get result as string
result = tool.process("document.pdf")

# Save to file
with open("result.md", "w", encoding="utf-8") as f:
    f.write(result)
```

### Video Transcription

```python
from power_ocr import transcribe_video
import os

# Prepare parameters
params = {
    "video_path": "video.mp4",
    "api_base": os.environ.get("VIDEO_OCR_API_URL"),
    "api_key": os.environ.get("VIDEO_OCR_API_KEY"),
    "model": os.environ.get("VIDEO_OCR_MODEL_NAME", "whisper-large-v3"),
    # Optional: specific language (otherwise auto-detected)
    # "language": "en"
}

# Process video
result = transcribe_video(params)

# Check for errors
if result["status"] == "error":
    print(f"Error: {result['error']}")
else:
    # Save transcription
    with open("transcript.md", "w", encoding="utf-8") as f:
        f.write(result["transcription"])
```

## License

[MIT License](LICENSE)