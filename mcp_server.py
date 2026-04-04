import anyio
import click
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from ingest import ingest_file, get_format_info, SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS
from ffmpeg_wrapper import FFmpegWrapper
from transcription import TranscriptionService
from clip_extractor import ClipExtractor, ClipBoundaryDetector, load_transcription

import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("agentic-tv-station")

ffmpeg = FFmpegWrapper()
clip_extractor = ClipExtractor(ffmpeg)
boundary_detector = ClipBoundaryDetector()


@mcp.tool()
def ingest_media(file_path: str) -> str:
    """Ingest and validate a media file (video or audio)"""
    media = ingest_file(file_path)
    return json.dumps({
        "path": media.path,
        "filename": media.filename,
        "format": media.format,
        "media_type": media.media_type,
        "size_bytes": media.size_bytes,
        "mime_type": media.mime_type,
    })


@mcp.tool()
def get_format_info(file_path: str) -> str:
    """Get detailed format information about a media file"""
    info = get_format_info(file_path)
    return json.dumps(info)


@mcp.tool()
def transcribe_media(file_path: str, language: str = None, output_path: str = None) -> str:
    """Transcribe audio from a media file"""
    service = TranscriptionService()
    result = service.transcribe(file_path, language=language)
    if output_path:
        Path(output_path).write_text(json.dumps(result))
    return json.dumps(result)


@mcp.tool()
def extract_audio(input_path: str, output_path: str) -> str:
    """Extract audio track from a video file"""
    result = ffmpeg.extract_audio(input_path, output_path)
    return json.dumps(result)


@mcp.tool()
def get_media_duration(file_path: str) -> str:
    """Get the duration of a media file in seconds"""
    duration = ffmpeg.get_duration(file_path)
    return json.dumps({"duration_seconds": duration})


@mcp.tool()
def get_video_info(file_path: str) -> str:
    """Get video stream information (resolution, codec, fps)"""
    info = ffmpeg.get_video_info(file_path)
    return json.dumps(info)


@mcp.tool()
def trim_media(input_path: str, output_path: str, start_seconds: float, duration_seconds: float) -> str:
    """Trim media file to a specific time range"""
    result = ffmpeg.trim(input_path, output_path, start_seconds, duration_seconds)
    return json.dumps(result)


@mcp.tool()
def find_clip_boundaries(transcription_path: str, min_duration: float = 5.0, max_duration: float = 120.0, silence_threshold: float = 2.0) -> str:
    """Find natural clip boundaries in a transcription"""
    transcription = load_transcription(transcription_path)
    boundary_detector.min_clip_duration = min_duration
    boundary_detector.max_clip_duration = max_duration
    boundary_detector.silence_threshold = silence_threshold
    boundaries = boundary_detector.find_boundaries(transcription)
    return json.dumps([
        {"start": s, "end": e, "duration": e - s}
        for s, e in boundaries
    ])


@mcp.tool()
def extract_clip(input_path: str, output_path: str, start_seconds: float, end_seconds: float) -> str:
    """Extract a clip from video based on timestamps"""
    result = clip_extractor.extract_clip(input_path, output_path, start_seconds, end_seconds)
    return json.dumps(result)


@mcp.tool()
def list_supported_formats() -> str:
    """List all supported video and audio formats"""
    return json.dumps({
        "video": list(SUPPORTED_VIDEO_FORMATS),
        "audio": list(SUPPORTED_AUDIO_FORMATS),
    })


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, help="Port to bind to")
def main(host: str, port: int):
    """Run the Agentic TV Station MCP Server."""
    anyio.run(mcp.run_stdio_async)


if __name__ == "__main__":
    main()
