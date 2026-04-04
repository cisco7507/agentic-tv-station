#!/usr/bin/env python3
"""Unit tests for ingest module."""

import pytest
import tempfile
import os
from pathlib import Path

from ingest import (
    validate_file, 
    ingest_file, 
    get_format_info,
    MediaFile,
    IngestError,
    FileNotFoundError,
    FileNotReadableError,
    UnsupportedFormatError
)


def test_validate_file_success():
    """Test successful file validation."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        tmp.write(b"fake content")
        tmp.flush()
        
        try:
            media_file = validate_file(tmp.name)
            assert isinstance(media_file, MediaFile)
            assert media_file.format == '.mp4'
            assert media_file.media_type == 'video'
            assert media_file.size == len(b"fake content")
        finally:
            os.unlink(tmp.name)


def test_validate_file_not_found():
    """Test validation of non-existent file."""
    with pytest.raises(FileNotFoundError):
        validate_file('/non/existent/file.mp4')


def test_validate_file_unsupported_format():
    """Test validation of unsupported file format."""
    with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp:
        tmp.write(b"fake content")
        tmp.flush()
        
        try:
            with pytest.raises(UnsupportedFormatError):
                validate_file(tmp.name)
        finally:
            os.unlink(tmp.name)


def test_ingest_file():
    """Test ingest_file function."""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        tmp.write(b"fake audio")
        tmp.flush()
        
        try:
            media_file = ingest_file(tmp.name)
            assert isinstance(media_file, MediaFile)
            assert media_file.format == '.mp3'
            assert media_file.media_type == 'audio'
        finally:
            os.unlink(tmp.name)


def test_get_format_info():
    """Test get_format_info function."""
    with tempfile.NamedTemporaryFile(suffix='.mov', delete=False) as tmp:
        tmp.write(b"fake video")
        tmp.flush()
        
        try:
            info = get_format_info(tmp.name)
            assert info['format'] == '.mov'
            assert info['media_type'] == 'video'
            assert info['size_bytes'] == len(b"fake video")
            assert 'mime_type' in info
        finally:
            os.unlink(tmp.name)


if __name__ == '__main__':
    pytest.main([__file__])