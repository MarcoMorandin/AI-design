#!/usr/bin/env python3

import argparse
import sys
import os
from dotenv import load_dotenv
from ..video_processor import transcribe_video
from ..utils.exceptions import ProcessingError

load_dotenv()


def main():
    """
    CLI entry point for video transcription.
    """
    parser = argparse.ArgumentParser(
        description="Transcribe video files using AI services."
    )
    parser.add_argument("input_file", help="The path to the video file to transcribe")
    parser.add_argument(
        "-o",
        "--output",
        help="Output markdown file path (default: based on input filename)",
    )
    parser.add_argument(
        "--api-base",
        help="API base URL for the transcription API",
        default=os.environ.get("VIDEO_OCR_API_URL"),
    )
    parser.add_argument(
        "--model",
        help="Model name to use for transcription (e.g. whisper-large-v3)",
        default=os.environ.get("VIDEO_OCR_MODEL_NAME", "whisper-large-v3"),
    )
    parser.add_argument(
        "--api-key",
        help="API key for the transcription service",
        default=os.environ.get("VIDEO_OCR_API_KEY"),
    )
    parser.add_argument(
        "--language",
        help="Specific language code (ISO-639-1) to use. If not provided, language will be auto-detected.",
    )

    args = parser.parse_args()

    # Validate required parameters
    if not args.api_base:
        print(
            "Error: Missing API base URL. Set VIDEO_OCR_API_URL environment variable or use --api-base",
            file=sys.stderr,
        )
        return 1

    if not args.api_key:
        print(
            "Error: Missing API key. Set VIDEO_OCR_API_KEY environment variable or use --api-key",
            file=sys.stderr,
        )
        return 1

    # Generate output filename if not specified
    if not args.output:
        base_name = os.path.splitext(os.path.basename(args.input_file))[0]
        args.output = f"{base_name}.md"

    try:
        # Prepare parameters for transcription
        transcription_params = {
            "video_path": args.input_file,
            "api_base": args.api_base,
            "api_key": args.api_key,
            "model": args.model,
        }

        # Add optional language parameter if specified
        if args.language:
            transcription_params["language"] = args.language

        print(f"Processing video: {args.input_file}")
        result = transcribe_video(transcription_params)

        if result["status"] == "error":
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        # Save the transcription to the output file
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result["transcription"])
        print(f"Transcription saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
