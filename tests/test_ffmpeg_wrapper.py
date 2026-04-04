#!/usr/bin/env python3
"""Unit tests for ffmpeg_wrapper module."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from ffmpeg_wrapper import FFmpegWrapper, FFmpegError


def test_ffmpeg_wrapper_init():
    """Test FFmpegWrapper initialization."""
    fw = FFmpegWrapper()
    assert fw is not None


@patch('ffmpeg_wrapper.subprocess.run')
def test_get_duration(mock_run):
    """Test get_duration method."""
    # Mock subprocess.run to return fake probe data
    mock_result = MagicMock()
    mock_result.stdout = '{"format": {"duration": "123.45"}}'
    mock_run.return_value = mock_result
    
    fw = FFmpegWrapper()
    duration = fw.get_duration('fake_video.mp4')
    
    assert duration == 123.45
    mock_run.assert_called_once()


@patch('ffmpeg_wrapper.subprocess.run')
def test_get_video_info(mock_run):
    """Test get_video_info method."""
    # Mock subprocess.run to return fake video info
    mock_result = MagicMock()
    mock_result.stdout = '''
{
    "streams": [
        {
            "codec_type": "video",
            "width": 1920,
            "height": 1080,
            "codec_name": "h264",
            "r_frame_rate": "30/1"
        }
    ]
}
'''
    mock_run.return_value = mock_result
    
    fw = FFmpegWrapper()
    info = fw.get_video_info('fake_video.mp4')
    
    assert info is not None
    assert info['width'] == 1920
    assert info['height'] == 1080
    assert info['codec'] == 'h264'
    assert info['fps'] == 30.0


def test_ffmpeg_error():
    """Test FFmpegError exception."""
    with pytest.raises(FFmpegError):
        raise FFmpegError("FFmpeg command failed")


if __name__ == '__main__':
    pytest.main([__file__])