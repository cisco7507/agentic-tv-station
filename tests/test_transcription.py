#!/usr/bin/env python3
"""Unit tests for transcription module."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from transcription import (
    TranscriptionService,
    TranscriptionError,
    TranscriptionAPIError,
    AudioExtractionError
)


def test_transcription_service_init():
    """Test TranscriptionService initialization."""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        service = TranscriptionService()
        assert service.api_key == 'test-key'
        assert service.model == 'whisper-1'


def test_transcription_service_init_no_key():
    """Test TranscriptionService initialization without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(TranscriptionError):
            TranscriptionService()


@patch('openai.OpenAI')
def test_transcribe(mock_openai_class):
    """Test transcribe method."""
    # Setup mock
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "This is a test transcription."
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # Create temp audio file
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        tmp.write(b"fake audio content")
        tmp.flush()
        
        try:
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
                service = TranscriptionService()
                result = service.transcribe(tmp.name, language='en')
                
                assert result['text'] == "This is a test transcription."
                assert result['model'] == 'whisper-1'
                assert result['language'] == 'en'
        finally:
            os.unlink(tmp.name)


@patch('openai.OpenAI')
def test_transcribe_video(mock_openai_class):
    """Test transcribe_video method."""
    # Setup mocks
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "Video transcription test."
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # Create temp video and audio files
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_tmp:
        video_path = video_tmp.name
        video_tmp.write(b"fake video content")
        video_tmp.flush()
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_tmp:
            audio_path = audio_tmp.name
            
            try:
                with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
                    service = TranscriptionService()
                    
                    # Mock FFmpegWrapper.extract_audio to do nothing
                    with patch('transcription.FFmpegWrapper') as mock_ffmpeg:
                        mock_ffmpeg_instance = MagicMock()
                        mock_ffmpeg.return_value = mock_ffmpeg_instance
                        
                        result = service.transcribe_video(
                            video_path,
                            audio_path=audio_path,
                            language='en'
                        )
                        
                        assert result['text'] == "Video transcription test."
                        assert result['model'] == 'whisper-1'
                        assert result['language'] == 'en'
                        
                        # Verify FFmpeg was called
                        mock_ffmpeg_instance.extract_audio.assert_called_once()
            finally:
                # Cleanup temp files
                for path in [video_path, audio_path]:
                    if os.path.exists(path):
                        os.unlink(path)


def test_transcription_error():
    """Test TranscriptionError exception."""
    with pytest.raises(TranscriptionError):
        raise TranscriptionError("Test transcription error")


if __name__ == '__main__':
    pytest.main([__file__])