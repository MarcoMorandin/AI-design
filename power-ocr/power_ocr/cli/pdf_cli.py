#!/usr/bin/env python3

import argparse
import sys
import os
from dotenv import load_dotenv
from ..pdf_processor import PdfTranscriptionTool
from ..utils.exceptions import ProcessingError

load_dotenv()


def main():
    """
    CLI entry point for PDF transcription.
    """
    parser = argparse.ArgumentParser(
        description="Transcribe PDF files using AI services."
    )
    parser.add_argument("input_file", help="The path to the PDF file to transcribe")
    parser.add_argument(
        "-o",
        "--output",
        help="Output markdown file path (default: based on input filename)",
    )
    parser.add_argument(
        "--api-base",
        help="API base URL for the LLM provider",
        default=os.environ.get("PDF_OCR_API_ENDPOINT"),
    )
    parser.add_argument(
        "--model",
        help="Model name to use for transcription",
        default=os.environ.get("PDF_OCR_MODEL_NAME"),
    )
    parser.add_argument(
        "--api-key",
        help="API key for the LLM provider",
        default=os.environ.get("PDF_OCR_API_KEY"),
    )

    args = parser.parse_args()

    # Validate required parameters
    if not args.api_base:
        print(
            "Error: Missing API base URL. Set PDF_OCR_API_ENDPOINT environment variable or use --api-base",
            file=sys.stderr,
        )
        return 1

    if not args.model:
        print(
            "Error: Missing model name. Set PDF_OCR_MODEL_NAME environment variable or use --model",
            file=sys.stderr,
        )
        return 1

    if not args.api_key:
        print(
            "Error: Missing API key. Set PDF_OCR_API_KEY environment variable or use --api-key",
            file=sys.stderr,
        )
        return 1

    # Generate output filename if not specified
    if not args.output:
        base_name = os.path.splitext(os.path.basename(args.input_file))[0]
        args.output = f"{base_name}.md"

    try:
        # Initialize the transcription tool
        tool = PdfTranscriptionTool(
            api_base=args.api_base,
            model_name=args.model,
            api_key=args.api_key,
        )

        # Process the PDF
        print(f"Processing PDF: {args.input_file}")
        result = tool.process(args.input_file)

        # Write the result to the output file
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Transcription saved to: {args.output}")

        return 0

    except ProcessingError as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
