import os
import tempfile
import logging
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil
import ffmpeg
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_CHUNK_SIZE_MB = 25


def transcribe_video(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transcribes a video file from the local filesystem.

    Args:
        parameters: Dictionary of parameters including:
            - video_path: Path to the video file on the local filesystem.
            - api_base: Base URL for the transcription API. Default: OpenAI base URL.
            - api_key: API key for the transcription service. Required.
            - model: Model to use for transcription (e.g. "whisper-large-v3"). Default: "whisper-large-v3".
    Returns:
        Dictionary with status and transcription results or error information.
    """
    try:
        # --- Configuration ---
        # Processing configuration
        chunk_size_seconds = 590
        audio_bitrate = "128k"

        # --- Get Parameters ---
        video_path_param = parameters.get("video_path")
        if not video_path_param:
            return _error_response("Missing required parameter: video_path")

        # Validate video path
        video_path = Path(video_path_param).resolve()  # Get absolute path
        if not video_path.is_file():
            return _error_response(
                f"Video file not found or is not a file: {video_path_param}"
            )

        # Language is auto-detected by default
        language = parameters.get("language")

        # API configuration
        api_base = parameters.get("api_base")
        api_key = parameters.get("api_key")
        model = parameters.get("model", "whisper-large-v3")

        # Validate API key
        if not api_key:
            return _error_response(
                "API key not found. Please provide it in parameters or set API_KEY environment variable."
            )

        # Generate a unique task ID (useful for temp files)
        task_id = str(uuid.uuid4())

        # --- Processing Steps ---
        # Create temporary directory for intermediate files (audio, chunks)
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Using temporary directory: {temp_dir}")

            # 1. Extract full audio from the provided video file
            full_audio_path = _extract_full_audio(
                str(video_path), task_id, temp_dir, audio_bitrate
            )

            # 2. Split audio into manageable chunks
            audio_chunks = _split_audio(
                full_audio_path,
                task_id,
                temp_dir,
                chunk_size_seconds,
                MAX_CHUNK_SIZE_MB,
            )

            # 3. Transcribe audio chunks using the API
            transcription = _transcribe_audio_chunks_with_openai(
                audio_chunks, language, api_base, api_key, model, chunk_size_seconds
            )

            return {"status": "success", "transcription": transcription.get("text", "")}

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return _error_response(f"Processing error: {str(e)}")


def _extract_full_audio(
    video_path: str, task_id: str, temp_dir: str, audio_bitrate: str
) -> str:
    """Extract full audio from video using ffmpeg into the temporary directory."""
    logger.info(f"Extracting full audio from video: {video_path}")
    try:
        # Define output path for full audio within the temp directory
        # Use task_id to ensure uniqueness if multiple processes run concurrently
        audio_filename = f"{task_id}_full_audio.mp3"
        audio_path = os.path.join(temp_dir, audio_filename)

        # Extract audio using ffmpeg
        (
            ffmpeg.input(video_path)
            .output(audio_path, acodec="libmp3lame", ab=audio_bitrate, vn=None)
            .overwrite_output()
            .run(
                capture_stdout=True, capture_stderr=True
            )  # Capture output for better debugging
        )

        logger.info(f"Full audio extracted successfully to: {audio_path}")
        return audio_path
    except Exception as e:
        logger.error(
            f"Unexpected error during audio extraction: {str(e)}", exc_info=True
        )
        raise RuntimeError(f"Unexpected error during audio extraction: {str(e)}")


def _split_audio(
    full_audio_path: str,
    task_id: str,
    temp_dir: str,
    chunk_size_seconds: int,
    MAX_CHUNK_SIZE_MB: int,
) -> List[str]:
    """Split audio into chunks for processing within the temporary directory."""
    logger.info(f"Splitting audio file: {full_audio_path}")
    try:
        # Create a dedicated subdirectory for chunks within the temp_dir
        chunk_dir = os.path.join(temp_dir, f"{task_id}_chunks")
        os.makedirs(chunk_dir, exist_ok=True)
        logger.info(f"Created chunk directory: {chunk_dir}")

        # Define chunk pattern
        chunk_pattern = os.path.join(chunk_dir, "chunk_%03d.mp3")

        # Split audio using ffmpeg
        try:
            (
                ffmpeg.input(full_audio_path)
                .output(
                    chunk_pattern,
                    f="segment",  # Use segment muxer for splitting
                    segment_time=chunk_size_seconds,  # Split duration
                    c="copy",  # Copy codec (faster if possible)
                    reset_timestamps=1,
                )  # Reset timestamps for each chunk
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)  # Capture output
            )
        except ffmpeg.Error as e:
            stderr = e.stderr.decode("utf8") if e.stderr else "No stderr"
            logger.error(f"FFmpeg error during audio splitting: {stderr}")

        # List generated chunks
        chunk_files = sorted(
            [
                os.path.join(chunk_dir, f)
                for f in os.listdir(chunk_dir)
                if f.startswith("chunk_") and f.endswith(".mp3")
            ]
        )

        logger.info(f"Generated {len(chunk_files)} audio chunks in {chunk_dir}")

        # Handle cases where splitting might fail or produce no chunks
        if not chunk_files:
            logger.warning(
                "Splitting resulted in zero chunk files. This might happen for very short audio."
            )
            # Check if original audio file itself is small enough to be used directly
            try:
                stats = os.stat(full_audio_path)
                file_size_mb = stats.st_size / (1024 * 1024)
                if file_size_mb < MAX_CHUNK_SIZE_MB:
                    logger.info(
                        f"Original audio file size ({file_size_mb:.2f} MB) is below the limit ({MAX_CHUNK_SIZE_MB} MB). Using it as a single chunk."
                    )
                    # Move the original audio file into the chunk directory structure expected by cleanup
                    single_chunk_path = os.path.join(
                        chunk_dir, os.path.basename(full_audio_path)
                    )
                    shutil.move(full_audio_path, single_chunk_path)
                    return [single_chunk_path]
                else:
                    raise RuntimeError(
                        f"Audio splitting failed to produce chunk files, and the original audio ({file_size_mb:.2f} MB) is too large."
                    )
            except FileNotFoundError:
                raise RuntimeError(
                    f"Original audio file not found after splitting attempt: {full_audio_path}"
                )

        return chunk_files

    except Exception as e:
        logger.error(f"Error during audio splitting process: {str(e)}", exc_info=True)
        raise RuntimeError(f"Error during audio splitting: {str(e)}")


def _transcribe_audio_chunks_with_openai(
    audio_chunks: List[str],
    language: Optional[str],
    api_base: str,
    api_key: str,
    model: str,
    chunk_size_seconds: int,
) -> Dict[str, Any]:
    """Transcribe multiple audio chunks using OpenAI SDK and combine results."""

    logger.info(
        f"Starting transcription for {len(audio_chunks)} audio chunks using API base: {api_base}"
    )

    if language:
        logger.info(f"Using specified language: {language}")
    else:
        logger.info("No language specified. Language will be auto-detected.")

    # Initialize the OpenAI client with correct base URL
    client = OpenAI(api_key=api_key, base_url=api_base)

    combined_text = ""
    segments = []
    current_offset = 0.0
    detected_language = None

    for i, chunk_path in enumerate(audio_chunks):
        logger.info(
            f"Transcribing chunk {i+1}/{len(audio_chunks)}: {os.path.basename(chunk_path)}"
        )

        try:
            # Check chunk size before processing (basic sanity check)
            if not os.path.exists(chunk_path):
                logger.warning(
                    f"Skipping chunk {i+1} as file does not exist: {chunk_path}"
                )
                continue
            stats = os.stat(chunk_path)
            if stats.st_size == 0:
                logger.warning(
                    f"Skipping chunk {i+1} as it has zero size: {os.path.basename(chunk_path)}"
                )
                # Estimate duration based on chunk_size_seconds to keep timeline consistent
                current_offset += chunk_size_seconds
                continue
            if (
                stats.st_size > MAX_CHUNK_SIZE_MB * 1024 * 1024
            ):  # Re-check against limit
                logger.warning(
                    f"Chunk {i+1} size ({stats.st_size / (1024*1024):.2f} MB) exceeds limit. API might reject it."
                )

            # Prepare API call parameters
            transcription_params = {
                "file": None,  # Will be set in the with block
                "model": model,
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
            }

            # Only add language parameter if specified (otherwise auto-detect)
            if language:
                transcription_params["language"] = language

            # Transcribe the chunk using OpenAI's SDK
            with open(chunk_path, "rb") as audio_file:
                transcription_params["file"] = audio_file
                response = client.audio.transcriptions.create(**transcription_params)

            # Parse response
            chunk_result = (
                response.model_dump() if hasattr(response, "model_dump") else response
            )

            # If this is the first successful chunk and we're auto-detecting language,
            # store the detected language
            if detected_language is None and chunk_result.get("language"):
                detected_language = chunk_result.get("language")
                logger.info(f"Language auto-detected as: {detected_language}")

            if chunk_result and chunk_result.get("text"):
                chunk_text = chunk_result["text"]
                combined_text += chunk_text + " "  # Add space between chunk texts

                # Use detailed segments if API provides them, otherwise approximate
                if chunk_result.get("segments"):
                    for seg in chunk_result["segments"]:
                        # Adjust segment times relative to the start of this chunk
                        start_time = current_offset + seg.get("start", 0)
                        end_time = current_offset + seg.get(
                            "end", chunk_size_seconds
                        )  # Fallback end time
                        segments.append(
                            {
                                "text": seg.get("text", ""),
                                "start": start_time,
                                "end": end_time,
                                # Include other segment details if available (id, seek, etc.)
                                "id": seg.get("id"),
                                "seek": seg.get("seek"),
                                "tokens": seg.get("tokens"),
                                "temperature": seg.get("temperature"),
                                "avg_logprob": seg.get("avg_logprob"),
                                "compression_ratio": seg.get("compression_ratio"),
                                "no_speech_prob": seg.get("no_speech_prob"),
                            }
                        )
                    # Advance offset based on the actual duration of the last segment from this chunk
                    # If detailed segments are not available, this might be less accurate
                    if chunk_result["segments"]:
                        last_segment_end = chunk_result["segments"][-1].get(
                            "end", chunk_size_seconds
                        )
                        current_offset += last_segment_end
                    else:  # Fallback if no detailed segments
                        current_offset += chunk_size_seconds

                else:
                    # Create a simple segment for this chunk with approximate timestamps
                    end_offset = current_offset + chunk_size_seconds  # Approximate end
                    segments.append(
                        {"text": chunk_text, "start": current_offset, "end": end_offset}
                    )
                    current_offset = (
                        end_offset  # Advance by the approximate chunk duration
                    )

            else:
                # Even if transcription is empty, advance the offset by chunk duration
                logger.warning(f"Chunk {i+1} produced no text.")
                current_offset += chunk_size_seconds

            logger.info(f"Chunk {i+1} processed successfully.")

        except Exception as e:
            logger.error(
                f"Transcription failed for chunk {i+1} ({os.path.basename(chunk_path)}): {str(e)}"
            )
            # Advance the offset even on failure to avoid large time gaps
            current_offset += chunk_size_seconds
            # Continue with other chunks rather than failing completely? Or raise? For now, continue.

    # Use detected language if we did auto-detection, otherwise use provided language
    final_language = detected_language if detected_language else language

    # Create combined transcription result
    result = {
        "text": combined_text.strip(),
        "segments": segments,
        "language": final_language,  # Include detected or specified language
    }

    logger.info(f"Combined transcription finished. Language: {final_language}")
    return result


def _error_response(message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    logger.error(message)
    return {"status": "error", "error": message}
