import os
import logging
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass


class TranscriptionAPIError(TranscriptionError):
    """Raised when API call fails."""
    pass


class AudioExtractionError(TranscriptionError):
    """Raised when audio extraction fails."""
    pass


class TranscriptionService:
    """Transcription service using OpenAI Whisper API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "whisper-1",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        
        if not self.api_key:
            raise TranscriptionError("API key required (set OPENAI_API_KEY)")
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        response_format: str = "json",
        temperature: float = 0.0,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Transcribe audio file using OpenAI Whisper API.
        
        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en')
            prompt: Optional prompt for better transcription
            response_format: Output format (json, text, srt, vtt)
            temperature: Sampling temperature (0.0 to 1.0)
            progress_callback: Optional callback for progress
            
        Returns:
            Dictionary with transcription text and metadata
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise TranscriptionError("openai package required: pip install openai")
        
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        try:
            with open(audio_path, "rb") as audio_file:
                kwargs = {
                    "file": audio_file,
                    "model": self.model,
                    "response_format": response_format,
                    "temperature": temperature,
                }
                if language:
                    kwargs["language"] = language
                if prompt:
                    kwargs["prompt"] = prompt
                
                if progress_callback:
                    progress_callback(25.0)
                
                response = client.audio.transcriptions.create(**kwargs)
                
                if progress_callback:
                    progress_callback(100.0)
                
                return {
                    "text": response.text if hasattr(response, "text") else str(response),
                    "model": self.model,
                    "language": language,
                }
                
        except Exception as e:
            raise TranscriptionAPIError(f"Transcription failed: {e}") from e
    
    def transcribe_video(
        self,
        video_path: str,
        audio_path: Optional[str] = None,
        temp_dir: Optional[str] = None,
        language: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Transcribe directly from video file (extracts audio first).
        
        Args:
            video_path: Path to video file
            audio_path: Optional output path for audio (temp if not provided)
            temp_dir: Directory for temp files
            language: Optional language code
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with transcription text and metadata
        """
        from ffmpeg_wrapper import FFmpegWrapper, FFmpegTranscodeError
        
        if progress_callback:
            progress_callback(10.0)
        
        if audio_path:
            extracted_audio = audio_path
        else:
            video_name = Path(video_path).stem
            temp_dir = temp_dir or os.environ.get("TEMP", "/tmp")
            extracted_audio = os.path.join(temp_dir, f"{video_name}_audio.mp3")
        
        try:
            fw = FFmpegWrapper()
            
            if progress_callback:
                progress_callback(30.0)
            
            fw.extract_audio(
                video_path,
                extracted_audio,
                progress_callback=lambda p: progress_callback(30.0 + p * 0.3) if progress_callback else None
            )
            
            if progress_callback:
                progress_callback(60.0)
            
            result = self.transcribe(
                extracted_audio,
                language=language,
                progress_callback=lambda p: progress_callback(60.0 + p * 0.4) if progress_callback else None
            )
            
            if not audio_path and os.path.exists(extracted_audio):
                os.remove(extracted_audio)
            
            return result
            
        except Exception as e:
            raise AudioExtractionError(f"Audio extraction failed: {e}") from e
