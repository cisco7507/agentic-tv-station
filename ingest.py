#!/usr/bin/env python3
"""Local file ingest pipeline for media files."""

import os
import mimetypes
from pathlib import Path
from typing import Optional

SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for streaming


class MediaFile:
    """Represents an ingested media file."""
    
    def __init__(self, path: str):
        self.path: Path = Path(path)
        self.size: Optional[int] = None
        self.format: Optional[str] = None
        self.media_type: Optional[str] = None
    
    def __repr__(self):
        return f"MediaFile(path={self.path}, format={self.format}, type={self.media_type})"


class IngestError(Exception):
    """Base exception for ingest errors."""
    pass


class FileNotFoundError(IngestError):
    """Raised when file doesn't exist."""
    pass


class FileNotReadableError(IngestError):
    """Raised when file isn't readable."""
    pass


class UnsupportedFormatError(IngestError):
    """Raised when file format isn't supported."""
    pass


def validate_file(path: str) -> MediaFile:
    """Validate a file exists, is readable, and has supported format.
    
    Args:
        path: Path to the media file
        
    Returns:
        MediaFile object with metadata
        
    Raises:
        FileNotFoundError: If file doesn't exist
        FileNotReadableError: If file isn't readable
        UnsupportedFormatError: If format isn't supported
    """
    media_file = MediaFile(path)
    
    if not media_file.path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not os.access(path, os.R_OK):
        raise FileNotReadableError(f"File not readable: {path}")
    
    media_file.size = media_file.path.stat().st_size
    media_file.format = media_file.path.suffix.lower()
    
    if media_file.format in SUPPORTED_VIDEO_FORMATS:
        media_file.media_type = "video"
    elif media_file.format in SUPPORTED_AUDIO_FORMATS:
        media_file.media_type = "audio"
    else:
        raise UnsupportedFormatError(f"Unsupported format: {media_file.format}")
    
    return media_file


def ingest_file(path: str) -> MediaFile:
    """Ingest a media file from local disk.
    
    Args:
        path: Path to the media file
        
    Returns:
        MediaFile object ready for processing
    """
    return validate_file(path)


def stream_file_chunks(path: str):
    """Generator that yields chunks of a file for large file handling.
    
    Args:
        path: Path to the file
        
    Yields:
        Bytes chunks of the file
    """
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            yield chunk


def get_format_info(path: str) -> dict:
    """Get detailed format information for a media file.
    
    Args:
        path: Path to the media file
        
    Returns:
        Dictionary with format details
    """
    media_file = validate_file(path)
    
    mime_type, _ = mimetypes.guess_type(path)
    
    return {
        "path": str(media_file.path),
        "filename": media_file.path.name,
        "format": media_file.format,
        "media_type": media_file.media_type,
        "size_bytes": media_file.size,
        "mime_type": mime_type,
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m ingest <media_file_path>")
        sys.exit(1)
    
    try:
        info = get_format_info(sys.argv[1])
        print(f"Ingested: {info}")
    except IngestError as e:
        print(f"Error: {e}")
        sys.exit(1)
