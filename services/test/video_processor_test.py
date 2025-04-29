import logging
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PowerOcr.VideoProcessor.VideoTranscriptionTool import (
    transcribe_video,
)
from dotenv import load_dotenv

load_dotenv()


API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():

    test_params = {
        "video_path": "./input/test.mp4",
        "output_format": "vtt",
        "language": "en",
        "timestamp": True,
        "api_url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "model": "whisper-large-v3",
        "api_key": API_KEY,
    }

    logger.info(f"Starting transcription for: {test_params['video_path']}")
    logger.info(f"Using model: {test_params['model']} via {test_params['api_url']}")
    logger.info(f"Output format: {test_params['output_format']}")

    result = transcribe_video(test_params)

    logger.info("\n--- Transcription Saved ---")
    if result.get("status") == "success":
        with open("./output/test-video-result.json", "w", encoding="utf-8") as f:
            f.write(
                json.dumps(result.get("transcription"), indent=2, ensure_ascii=False)
            )


if __name__ == "__main__":
    # Install the required packages if not already installed (ffmpeg-python, requests)
    main()
