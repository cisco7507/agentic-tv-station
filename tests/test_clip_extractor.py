#!/usr/bin/env python3
"""Unit tests for clip_extractor module."""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from clip_extractor import (
    TranscriptionSegment,
    Transcription,
    ClipBoundaryDetector,
    ClipExtractor,
    ClipExtractionError
)


def test_transcription_segment():
    """Test TranscriptionSegment creation."""
    segment = TranscriptionSegment(start=0.0, end=5.0, text="Hello world")
    assert segment.start == 0.0
    assert segment.end == 5.0
    assert segment.text == "Hello world"


def test_transcription():
    """Test Transcription creation and methods."""
    segments = [
        TranscriptionSegment(start=0.0, end=5.0, text="Hello"),
        TranscriptionSegment(start=5.0, end=10.0, text="world")
    ]
    transcription = Transcription(segments=segments)
    
    assert len(transcription.segments) == 2
    assert transcription.duration == 10.0
    # Text is not stored directly, but we can verify it through segments
    full_text = " ".join(s.text for s in transcription.segments)
    assert full_text == "Hello world"


def test_transcription_from_json():
    """Test Transcription.from_json method."""
    # Create a temporary JSON file
    import tempfile
    import json
    
    json_data = {
        "metadata": {"test": "data"},
        "segments": [
            {"start": 0.0, "end": 5.0, "text": "Hello"},
            {"start": 5.0, "end": 10.0, "text": "world"}
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        json.dump(json_data, tmp)
        tmp_path = tmp.name
    
    try:
        transcription = Transcription.from_json(tmp_path)
        
        assert len(transcription.segments) == 2
        assert transcription.metadata == {"test": "data"}
        full_text = " ".join(s.text for s in transcription.segments)
        assert full_text == "Hello world"
        assert transcription.segments[0].start == 0.0
        assert transcription.segments[1].end == 10.0
    finally:
        os.unlink(tmp_path)


def test_clip_boundary_detector():
    """Test ClipBoundaryDetector initialization."""
    detector = ClipBoundaryDetector(min_clip_duration=5.0, max_clip_duration=120.0)
    assert detector.min_clip_duration == 5.0
    assert detector.max_clip_duration == 120.0
    assert detector.silence_threshold == 2.0  # default


def test_clip_boundary_detector_with_custom_params():
    """Test ClipBoundaryDetector with custom parameters."""
    detector = ClipBoundaryDetector(
        min_clip_duration=3.0,
        max_clip_duration=60.0,
        silence_threshold=1.5
    )
    assert detector.min_clip_duration == 3.0
    assert detector.max_clip_duration == 60.0
    assert detector.silence_threshold == 1.5


def test_clip_boundary_detector_find_boundaries():
    """Test finding boundaries in transcription."""
    # Create transcription with clear boundaries (silence gaps)
    segments = [
        TranscriptionSegment(start=0.0, end=5.0, text="First sentence."),
        TranscriptionSegment(start=5.0, end=10.0, text="Second sentence."),
        # 3 second gap
        TranscriptionSegment(start=13.0, end=18.0, text="Third sentence."),
        TranscriptionSegment(start=18.0, end=23.0, text="Fourth sentence."),
        # 5 second gap
        TranscriptionSegment(start=28.0, end=33.0, text="Fifth sentence."),
    ]
    transcription = Transcription(segments=segments)
    
    detector = ClipBoundaryDetector(min_clip_duration=5.0, max_clip_duration=15.0)
    boundaries = detector.find_boundaries(transcription)
    
    # Should find boundaries at the gaps
    # Gap 1: 10.0 to 13.0 (3 seconds) - should be a boundary
    # Gap 2: 23.0 to 28.0 (5 seconds) - should be a boundary
    assert len(boundaries) >= 2


def test_clip_extractor_init():
    """Test ClipExtractor initialization."""
    with patch('clip_extractor.FFmpegWrapper') as mock_ffmpeg:
        mock_ffmpeg_instance = MagicMock()
        mock_ffmpeg.return_value = mock_ffmpeg_instance
        extractor = ClipExtractor(mock_ffmpeg_instance)
        assert extractor is not None


def test_clip_extraction_error():
    """Test ClipExtractionError exception."""
    with pytest.raises(ClipExtractionError):
        raise ClipExtractionError("Test clip extraction error")


if __name__ == '__main__':
    pytest.main([__file__])