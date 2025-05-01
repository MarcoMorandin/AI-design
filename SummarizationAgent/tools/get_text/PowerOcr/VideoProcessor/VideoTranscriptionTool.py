import os
import json
import tempfile
import logging
import uuid
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil  # Import shutil for cleanup if needed later
import ffmpeg  # Explicitly import ffmpeg here

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
            - output_format: Format for output (plain, vtt). Default: "plain".
            - language: Source language code (ISO 639-1). Default: "en".
            - timestamp: Whether to include timestamps (relevant for VTT). Default: False.
            - api_url: Base URL for the transcription API. Default: Groq Whisper endpoint.
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

        # Get configuration parameters with defaults
        output_format = parameters.get("output_format", "plain")
        language = parameters.get("language", "en")
        include_timestamps = parameters.get("timestamp", False)

        # API configuration
        api_url = parameters.get(
            "api_url", "https://api.groq.com/openai/v1/audio/transcriptions"
        )
        api_key = parameters.get("api_key", "")
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
            #    The original video file remains untouched at its original location.
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
            transcription = _transcribe_audio_chunks(
                audio_chunks, language, api_url, api_key, model, chunk_size_seconds
            )

            # 4. Clean up chunk files (chunk directory is within temp_dir, so handled by TemporaryDirectory context manager)
            #    We can still explicitly log the cleanup if desired using _cleanup_chunks,
            #    but the actual deletion is managed by the `with` statement.
            _cleanup_chunks(
                task_id, temp_dir
            )  # Logs cleanup, directory removed by context manager

            # 5. Format the final output
            result = _format_output(transcription, output_format, include_timestamps)

            return {"status": "success", "transcription": result}

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
            # Sometimes ffmpeg finishes but logs errors (e.g., slight mismatches).
            # Check if *any* chunks were created before re-raising fully.
            chunk_files_check = [
                f
                for f in os.listdir(chunk_dir)
                if f.startswith("chunk_") and f.endswith(".mp3")
            ]
            if not chunk_files_check:
                raise RuntimeError(
                    f"FFmpeg error during audio splitting and no chunks were created: {stderr}"
                ) from e
            else:
                logger.warning(
                    f"FFmpeg reported errors during splitting, but chunks were created. Proceeding cautiously. Error: {stderr}"
                )

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


def _transcribe_audio_chunks(
    audio_chunks: List[str],
    language: str,
    api_url: str,
    api_key: str,
    model: str,
    chunk_size_seconds: int,  # Used for approximate segment timing
) -> Dict[str, Any]:
    """Transcribe multiple audio chunks and combine results."""

    logger.info(
        f"Starting transcription for {len(audio_chunks)} audio chunks using API: {api_url}"
    )

    combined_text = ""
    segments = []
    current_offset = 0.0

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

            # Transcribe chunk - use the existing _transcribe_audio_file helper
            # Pass only necessary parameters
            chunk_result = _transcribe_audio_file_with_segments(
                audio_path=chunk_path,
                api_url=api_url,
                api_key=api_key,
                model=model,
                language=language,
            )

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

    # Create combined transcription result
    result = {
        "text": combined_text.strip(),
        "segments": segments,
        "language": language,  # Include language used in the final output
    }

    logger.info("Combined transcription finished")
    return result


def _transcribe_audio_file_with_segments(
    audio_path: str, api_url: str, api_key: str, model: str, language: Optional[str]
) -> Dict[str, Any]:
    """
    Transcribe a single audio file using the specified API endpoint.
    Attempts to get detailed segments if the API supports it via response_format.
    Returns the full JSON response dictionary from the API.
    """

    try:
        headers = {"Authorization": f"Bearer {api_key}"}

        with open(audio_path, "rb") as audio_file:
            files = {
                "file": (
                    os.path.basename(audio_path),
                    audio_file,
                    "audio/mpeg",
                )
            }

            # Prepare form data - include timestamp granularity if aiming for segments
            data = {
                "model": model,
                "response_format": "verbose_json",  # Request segments and detailed info
                "timestamp_granularities[]": "segment",  # Request segment-level timestamps
            }
            if language:
                data["language"] = language

            logger.debug(
                f"Sending transcription request to {api_url} for {os.path.basename(audio_path)} with data: {data}"
            )

            response = requests.post(api_url, headers=headers, files=files, data=data)

            response.raise_for_status()

            result = response.json()
            logger.debug(f"API response received for {os.path.basename(audio_path)}")

            if not isinstance(result, dict):
                logger.error(f"API response is not a dictionary: {result}")
                raise RuntimeError("Invalid API response format.")
            if "text" not in result:
                logger.warning(
                    f"Transcription response for {os.path.basename(audio_path)} missing 'text' field."
                )
                return result

            return result  # Return the full dictionary

    except requests.exceptions.RequestException as e:
        error_msg = f"API request error for {os.path.basename(audio_path)}: {str(e)}"
        status_code = -1
        details = "N/A"
        if hasattr(e, "response") and e.response is not None:
            status_code = e.response.status_code
            error_msg += f", Status code: {status_code}"
            try:
                details = e.response.json()
                error_msg += f", Details: {json.dumps(details)}"
            except json.JSONDecodeError:
                details = e.response.text
                error_msg += f", Response body: {details[:500]}..."
            except Exception:
                pass
        logger.error(error_msg)
        raise RuntimeError(
            f"API Transcription Failed (Status: {status_code}): {details}"
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error during single file transcription ({os.path.basename(audio_path)}): {str(e)}",
            exc_info=True,
        )
        raise RuntimeError(f"Unexpected transcription error: {str(e)}")


def _cleanup_chunks(task_id: str, temp_dir: str) -> None:
    """Logs the cleanup of temporary chunk files. Actual deletion handled by TemporaryDirectory."""
    chunk_dir = os.path.join(temp_dir, f"{task_id}_chunks")
    if os.path.exists(chunk_dir):
        logger.info(f"Chunk directory {chunk_dir} will be cleaned up automatically.")
    else:
        logger.info(
            "No chunk directory found to clean up (might be due to single chunk processing or prior error)."
        )


def _format_output(
    transcription: Dict[str, Any], output_format: str, include_timestamps: bool
) -> Any:
    """Format the transcription according to requested output format."""
    logger.info(
        f"Formatting output as: {output_format}, Include Timestamps: {include_timestamps}"
    )

    # Always use segments if available, especially for VTT
    segments = transcription.get("segments")

    if output_format == "vtt":
        if segments:
            return _format_as_vtt(segments)
        else:
            # Fallback if no segments (should be rare with verbose_json)
            logger.warning(
                "No segments found in transcription data for VTT formatting. Creating a single VTT entry."
            )
            return _format_as_vtt(
                [{"text": transcription.get("text", ""), "start": 0, "end": 0}]
            )  # Use 0 timestamps as fallback
    elif output_format == "json":
        # Return the full structured transcription data
        return transcription
    else:  # Default to plain text
        if include_timestamps and segments:
            # Create plain text with approximate timestamps prepended
            formatted_lines = []
            for segment in segments:
                start_time = _format_time_simple(segment.get("start", 0))
                formatted_lines.append(
                    f"[{start_time}] {segment.get('text', '').strip()}"
                )
            return "\n".join(formatted_lines)
        else:
            # Just return the combined text
            return transcription.get("text", "")


def _format_as_vtt(segments: list) -> str:
    """Format transcription segments as WebVTT subtitle format."""
    lines = ["WEBVTT", ""]
    if not segments:
        logger.warning("Attempting to format VTT with empty segments list.")
        return "\n".join(lines)  # Return minimal valid VTT

    for i, segment in enumerate(segments):
        if not isinstance(segment, dict):
            logger.warning(
                f"Segment item {i} is not a dictionary: {segment}. Skipping."
            )
            continue

        start = _format_time_vtt(segment.get("start", 0))  # Default to 0 if missing
        end = _format_time_vtt(
            segment.get("end", segment.get("start", 0))
        )  # Default end to start if missing
        text = segment.get("text", "").strip()  # Default to empty string

        if not text:
            logger.debug(f"Skipping empty segment at {start} --> {end}")
            continue  # Don't add segments with no text

        # VTT standard: Use segment index or a unique ID if available
        lines.append(f"{i+1}")  # Simple index as identifier
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # Blank line separator

    return "\n".join(lines)


def _format_time_vtt(seconds: float) -> str:
    """Convert seconds to WebVTT time format (HH:MM:SS.mmm)."""
    if seconds < 0:
        seconds = 0  # Handle potential negative timestamps gracefully
    milliseconds = int((seconds * 1000) % 1000)
    total_seconds = int(seconds)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}.{milliseconds:03d}"


def _format_time_simple(seconds: float) -> str:
    """Convert seconds to simple MM:SS format."""
    if seconds < 0:
        seconds = 0
    total_seconds = int(seconds)
    secs = total_seconds % 60
    mins = total_seconds // 60
    return f"{mins:02d}:{secs:02d}"


def _error_response(message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    logger.error(message)
    return {"status": "error", "error": message}
