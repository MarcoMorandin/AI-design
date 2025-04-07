# app/services/video_processing.py
import whisper
import asyncio
import logging
from pathlib import Path
from moviepy import VideoFileClip
from app.core.config import settings
from app.utils.file_handler import cleanup_files # Import cleanup if used within service
from typing import Optional # <--- Import Optional

logger = logging.getLogger(__name__)

# (Keep the synchronous helper functions _extract_audio_sync, _transcribe_audio_sync)
def _extract_audio_sync(video_path: Path, audio_path: Path):
    """Synchronous audio extraction logic."""
    video_clip = None
    audio_clip = None
    try:
        logger.info(f"Extracting audio from {video_path} to {audio_path}...")
        video_clip = VideoFileClip(str(video_path)) # moviepy needs string paths
        if video_clip.audio is None:
             raise ValueError(f"Video file '{video_path.name}' does not contain an audio track.")
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(str(audio_path), codec='mp3', bitrate='192k', logger=None) # Disable moviepy progress bar logging if desired
        logger.info(f"Audio extracted successfully for {video_path.name}")
    except Exception as e:
         logger.error(f"Moviepy failed to extract audio from {video_path.name}: {e}", exc_info=True)
         raise # Re-raise the exception to be caught by the caller
    finally:
        if audio_clip: audio_clip.close()
        if video_clip: video_clip.close()
        # import gc; gc.collect() # Uncomment if memory leaks are suspected


def _transcribe_audio_sync(audio_path: Path, model_name: str) -> Optional[str]:
    """Synchronous transcription logic."""
    try:
        logger.info(f"Loading Whisper model '{model_name}'...")
        # Consider GPU detection: torch.cuda.is_available()
        model = whisper.load_model(model_name)
        logger.info(f"Starting transcription for {audio_path.name} (this may take a while)...")
        result = model.transcribe(str(audio_path), fp16=False) # fp16 based on GPU availability?
        logger.info(f"Transcription completed for {audio_path.name}.")
        transcript = result.get('text')
        if not transcript:
             logger.warning(f"Transcription result for {audio_path.name} was empty.")
        return transcript
    except Exception as e:
        logger.error(f"Whisper transcription failed for {audio_path.name}: {e}", exc_info=True)
        raise # Re-raise

async def extract_audio(video_path: Path, audio_path: Path) -> bool:
    """Extracts audio from a video file (async wrapper)."""
    try:
        loop = asyncio.get_event_loop()
        # Run the synchronous, CPU-bound function in a thread pool executor
        await loop.run_in_executor(None, _extract_audio_sync, video_path, audio_path)
        return True
    except Exception as e:
        # Logging is done within _extract_audio_sync or here if needed
        logger.error(f"Audio extraction process failed for {video_path.name}: {e}")
        return False

async def transcribe_audio(audio_path: Path) -> Optional[str]:
    """Transcribes audio using Whisper (async wrapper)."""
    try:
        loop = asyncio.get_event_loop()
        # Run the synchronous, CPU/GPU-bound function in a thread pool executor
        transcript = await loop.run_in_executor(None, _transcribe_audio_sync, audio_path, settings.WHISPER_MODEL)
        return transcript
    except Exception as e:
        # Logging is done within _transcribe_audio_sync or here
        logger.error(f"Audio transcription process failed for {audio_path.name}: {e}")
        return None