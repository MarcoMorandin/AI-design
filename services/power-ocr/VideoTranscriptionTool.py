import os
import json
import tempfile
import logging
import uuid
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def transcribe_video(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """    
    Args:
        parameters: Dictionary of parameters including:
            - video_url: URL to the video file
            - output_format: Format for output (plain, vtt)
            - language: Source language code (ISO 639-1)
            - timestamp: Whether to include timestamps
            - api_url: Base URL for the transcription API
            - api_key: API key for the transcription service
            - model: Model to use for transcription (e.g. "whisper-large-v3")
    Returns:
        Dictionary with status and transcription results
    """
    try:
        # Processing configuration
        temp_dir = tempfile.gettempdir()
        chunk_size_seconds = 590
        max_chunk_size_mb = 25
        audio_bitrate = "128k"
        
        video_url = parameters.get("video_url")
        if not video_url:
            return _error_response("Missing required parameter: video_url")
        
        # Get configuration parameters with defaults
        output_format = parameters.get("output_format", "plain")
        language = parameters.get("language", "en")
        include_timestamps = parameters.get("timestamp", False)
        
        # API configuration
        api_url = parameters.get("api_url", "https://api.groq.com/openai/v1/audio/transcriptions")
        api_key = parameters.get("api_key", "")
        model = parameters.get("model", "whisper-large-v3")
        
        # Validate API key
        if not api_key:
            return _error_response("API key not found. Please provide it in parameters or set API_KEY environment variable.")
        
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video
            video_path = os.path.join(temp_dir, f"{task_id}_input_video.mp4")
            _download_video(video_url, video_path)
            
            # Extract full audio
            full_audio_path = _extract_full_audio(video_path, task_id, temp_dir, audio_bitrate)
            
            # Split audio into chunks
            audio_chunks = _split_audio(full_audio_path, task_id, temp_dir, chunk_size_seconds, max_chunk_size_mb)
            
            # Transcribe audio chunks using API
            transcription = _transcribe_audio_chunks(
                audio_chunks, 
                language, 
                api_url,
                api_key, 
                model,
                chunk_size_seconds
            )
            
            # Clean up chunks
            _cleanup_chunks(task_id, temp_dir)
            
            # Format output
            result = _format_output(transcription, output_format, include_timestamps)
            
            return {
                "status": "success",
                "transcription": result
            }
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return _error_response(f"Processing error: {str(e)}")

def _download_video(url: str, output_path: str) -> None:
    """Download video from URL to local path."""
    logger.info(f"Downloading video from: {url}")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info("Video download complete")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to download video: {str(e)}")

def _extract_full_audio(video_path: str, task_id: str, temp_dir: str, audio_bitrate: str) -> str:
    """Extract full audio from video using ffmpeg."""
    logger.info("Extracting full audio from video")
    try:
        # Define output path for full audio
        stem = Path(video_path).stem
        audio_path = os.path.join(temp_dir, f"{stem}_full_audio.mp3")
        
        # Extract audio using ffmpeg
        import ffmpeg
        ffmpeg.input(video_path) \
            .output(audio_path, acodec='libmp3lame', ab=audio_bitrate, vn=None) \
            .run(quiet=False, overwrite_output=True)
        
        logger.info(f"Full audio extraction complete: {audio_path}")
        return audio_path
    except Exception as e:
        raise RuntimeError(f"FFmpeg error during audio extraction: {str(e)}")

def _split_audio(full_audio_path: str, task_id: str, temp_dir: str, 
                chunk_size_seconds: int, max_chunk_size_mb: int) -> List[str]:
    """Split audio into chunks for processing."""
    logger.info(f"Splitting audio into chunks")
    try:
        # Create chunk directory
        chunk_dir = os.path.join(temp_dir, f"{task_id}_chunks")
        os.makedirs(chunk_dir, exist_ok=True)
        
        # Define chunk pattern
        chunk_pattern = os.path.join(chunk_dir, "chunk_%03d.mp3")
        
        # Split audio using ffmpeg
        import ffmpeg
        ffmpeg.input(full_audio_path) \
            .output(chunk_pattern, 
                   f="segment", 
                   segment_time=chunk_size_seconds,
                   c="copy",
                   reset_timestamps=1) \
            .run(quiet=True, overwrite_output=True)
        
        # List generated chunks
        chunk_files = sorted([
            os.path.join(chunk_dir, f) 
            for f in os.listdir(chunk_dir) 
            if f.startswith("chunk_") and f.endswith(".mp3")
        ])
        
        logger.info(f"Generated {len(chunk_files)} audio chunks")
        
        # If no chunks were created, check if original is small enough
        if not chunk_files:
            logger.warning("Splitting resulted in zero chunk files. Original file might be too short.")
            # Check if original file is under size limit
            stats = os.stat(full_audio_path)
            if stats.st_size < max_chunk_size_mb * 1024 * 1024:
                logger.info("Original file seems small enough, using it directly.")
                return [full_audio_path]
            else:
                raise RuntimeError("Audio splitting failed to produce chunk files for a large input.")
        
        return chunk_files
        
    except Exception as e:
        raise RuntimeError(f"Error during audio splitting: {str(e)}")

def _transcribe_audio_chunks(
    audio_chunks: List[str], 
    language: str, 
    api_url: str,
    api_key: str,
    model: str,
    chunk_size_seconds: int
) -> Dict[str, Any]:
    """Transcribe multiple audio chunks and combine results."""
    logger.info(f"Starting transcription for {len(audio_chunks)} audio chunks using API: {api_url}")
    
    combined_text = ""
    segments = []
    start_offset = 0
    
    for i, chunk_path in enumerate(audio_chunks):
        logger.info(f"Transcribing chunk {i+1}/{len(audio_chunks)}: {os.path.basename(chunk_path)}")
        
        try:
            # Check chunk size before processing
            stats = os.stat(chunk_path)
            if stats.st_size == 0:
                logger.warning(f"Skipping chunk {i+1} as it has zero size.")
                continue
            
            # Transcribe chunk
            chunk_text = _transcribe_audio_file(chunk_path, api_url, api_key, model, language)
            
            if chunk_text:
                combined_text += chunk_text + " "
                
                # Create a simple segment for this chunk with approximate timestamps
                end_offset = start_offset + chunk_size_seconds
                segments.append({
                    "text": chunk_text,
                    "start": start_offset,
                    "end": end_offset
                })
                start_offset = end_offset
            
            logger.info(f"Chunk {i+1} transcribed successfully")
            
        except Exception as e:
            logger.error(f"Transcription failed for chunk {i+1}: {str(e)}")
            # Continue with other chunks rather than failing completely
    
    # Create combined transcription result
    result = {
        "text": combined_text.strip(),
        "segments": segments
    }
    
    logger.info("Combined transcription finished")
    return result

def _transcribe_audio_file(audio_path: str, api_url: str, api_key: str, model: str, language: str) -> str:
    """
    Transcribe a single audio file using the specified API endpoint.
    Uses the OpenAI-compatible API format which is also supported by other providers.
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # Prepare the file for upload
        with open(audio_path, 'rb') as audio_file:
            files = {
                'file': (os.path.basename(audio_path), audio_file, 'audio/mpeg')
            }
            
            # Prepare form data
            data = {
                'model': model
            }
            
            # Add language if specified (supported by most providers)
            if language:
                data['language'] = language
            
            # Send request to API
            response = requests.post(
                api_url,
                headers=headers,
                files=files,
                data=data
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            if 'text' in result:
                return result['text']
            else:
                logger.warning("Transcription response did not contain text")
                return ""
                
    except requests.exceptions.RequestException as e:
        error_msg = f"API request error: {str(e)}"
        if hasattr(e, 'response') and e.response:
            error_msg += f", Status code: {e.response.status_code}"
            try:
                error_details = e.response.json()
                error_msg += f", Details: {json.dumps(error_details)}"
            except:
                pass
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def _cleanup_chunks(task_id: str, temp_dir: str) -> None:
    """Clean up temporary chunk files."""
    chunk_dir = os.path.join(temp_dir, f"{task_id}_chunks")
    try:
        if os.path.exists(chunk_dir):
            import shutil
            shutil.rmtree(chunk_dir)
            logger.info(f"Cleaned up chunk directory: {chunk_dir}")
    except Exception as e:
        logger.error(f"Error cleaning up chunk directory: {str(e)}")

def _format_output(transcription: Dict[str, Any], output_format: str, include_timestamps: bool) -> Any:
    """Format the transcription according to requested output format."""
    logger.info(f"Formatting output as: {output_format}")

    if output_format == "vtt":
        if transcription.get("segments"):
            return _format_as_vtt(transcription["segments"])
        else:
            return _format_as_vtt([{"text": transcription["text"], "start": 0, "end": 0}])
    
    else:  # plain text
        return transcription["text"]

def _format_as_vtt(segments: list) -> str:
    """Format transcription as WebVTT subtitle format."""
    lines = ["WEBVTT", ""]
    for i, segment in enumerate(segments):
        # Convert seconds to WebVTT time format (HH:MM:SS.mmm)
        start = _format_time_vtt(segment["start"])
        end = _format_time_vtt(segment["end"])
        
        lines.append(f"{start} --> {end}")
        lines.append(segment["text"].strip())
        lines.append("")
    
    return "\n".join(lines)

def _format_time_vtt(seconds: float) -> str:
    """Convert seconds to WebVTT time format (HH:MM:SS.mmm)."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"

def _error_response(message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    logger.error(message)
    return {
        "status": "error",
        "error": message
    }


if __name__ == "__main__":
    test_params = {
        "video_url": "https://streaming.l2l.cineca.it/p/126/sp/12600/serveFlavor/entryId/0_6ovdq6uk/v/2/ev/4/flavorId/0_kj6um11d/forceproxy/true/name/a.mp4?__hdnea__=st=1745584942~exp=1745610142~acl=/p/126/sp/12600/serveFlavor/entryId/0_6ovdq6uk/v/2/ev/4/flavorId/0_kj6um11d/forceproxy/true/name/a.mp4",
        "output_format": "vtt",
        "language": "it",
        "timestamp": True,
        # API configuration
        "api_url": "https://api.groq.com/openai/v1/audio/transcriptions",  # Groq with OpenAI-compatible endpoint
        "model": "whisper-large-v3",
        "api_key": os.environ.get("API_KEY")
    }
    
    result = transcribe_video(test_params)
    print(json.dumps(result, indent=2))