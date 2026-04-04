#!/usr/bin/env python3
"""FFmpeg wrapper abstraction layer for media processing."""

import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Base exception for FFmpeg errors."""
    pass


class FFmpegNotFoundError(FFmpegError):
    """Raised when FFmpeg is not installed."""
    pass


class FFmpegExecutionError(FFmpegError):
    """Raised when FFmpeg command fails."""
    pass


class FFmpegProbeError(FFmpegError):
    """Raised when ffprobe fails."""
    pass


@dataclass
class MediaStream:
    """Represents a media stream within a file."""
    index: int
    codec_type: str
    codec_name: str
    bit_rate: Optional[str] = None
    duration: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sample_rate: Optional[str] = None
    channels: Optional[int] = None
    channel_layout: Optional[str] = None


@dataclass
class MediaInfo:
    """Complete media file information."""
    filename: str
    format_name: str
    duration: float
    size_bytes: int
    bit_rate: str
    streams: List[MediaStream]


@dataclass
class TranscodeProgress:
    """Progress information for transcode operations."""
    frame: int
    fps: float
    size: int
    time: str
    bitrate: float
    speed: float
    progress_percent: float


def find_ffmpeg() -> Tuple[str, str]:
    """Find FFmpeg and ffprobe executables.
    
    Returns:
        Tuple of (ffmpeg_path, ffprobe_path)
        
    Raises:
        FFmpegNotFoundError: If FFmpeg is not installed
    """
    try:
        result = subprocess.run(
            ['which', 'ffmpeg'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise FFmpegNotFoundError("FFmpeg not found in PATH")
        ffmpeg_path = result.stdout.strip()
        
        result = subprocess.run(
            ['which', 'ffprobe'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise FFmpegNotFoundError("ffprobe not found in PATH")
        ffprobe_path = result.stdout.strip()
        
        return ffmpeg_path, ffprobe_path
    except Exception as e:
        raise FFmpegNotFoundError(f"Failed to find FFmpeg: {e}")


FFMPEG_PATH, FFPROBE_PATH = find_ffmpeg()


def parse_stream(stream_data: Dict[str, Any]) -> MediaStream:
    """Parse stream data into MediaStream object."""
    return MediaStream(
        index=stream_data.get('index', 0),
        codec_type=stream_data.get('codec_type', ''),
        codec_name=stream_data.get('codec_name', ''),
        bit_rate=stream_data.get('bit_rate'),
        duration=stream_data.get('duration'),
        width=stream_data.get('width'),
        height=stream_data.get('height'),
        sample_rate=stream_data.get('sample_rate'),
        channels=stream_data.get('channels'),
        channel_layout=stream_data.get('channel_layout'),
    )


def probe(input_path: str) -> MediaInfo:
    """Get media file information using ffprobe.
    
    Args:
        input_path: Path to the media file
        
    Returns:
        MediaInfo object with complete file information
        
    Raises:
        FFmpegProbeError: If probe fails
    """
    cmd = [
        FFPROBE_PATH,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        
        format_info = data.get('format', {})
        streams_data = data.get('streams', [])
        
        streams = [parse_stream(s) for s in streams_data]
        
        return MediaInfo(
            filename=format_info.get('filename', input_path),
            format_name=format_info.get('format_name', ''),
            duration=float(format_info.get('duration', 0)),
            size_bytes=int(format_info.get('size', 0)),
            bit_rate=format_info.get('bit_rate', ''),
            streams=streams
        )
    except subprocess.CalledProcessError as e:
        raise FFmpegProbeError(f"ffprobe failed: {e.stderr}")
    except json.JSONDecodeError as e:
        raise FFmpegProbeError(f"Failed to parse ffprobe output: {e}")


def transcode(
    input_path: str,
    output_path: str,
    video_codec: Optional[str] = None,
    audio_codec: Optional[str] = None,
    video_bitrate: Optional[str] = None,
    audio_bitrate: Optional[str] = None,
    resolution: Optional[str] = None,
    progress_callback: Optional[Callable[[TranscodeProgress], None]] = None,
) -> None:
    """Transcode media file to different format/codec.
    
    Args:
        input_path: Path to input media file
        output_path: Path to output media file
        video_codec: Video codec (e.g., 'libx264', 'libvpx')
        audio_codec: Audio codec (e.g., 'aac', 'libmp3lame')
        video_bitrate: Video bitrate (e.g., '1M', '500k')
        audio_bitrate: Audio bitrate (e.g., '128k', '192k')
        resolution: Output resolution (e.g., '1920x1080', '1280x720')
        progress_callback: Optional callback for progress updates
        
    Raises:
        FFmpegExecutionError: If transcode fails
    """
    cmd = [FFMPEG_PATH, '-y', '-i', input_path]
    
    if video_codec:
        cmd.extend(['-c:v', video_codec])
    if audio_codec:
        cmd.extend(['-c:a', audio_codec])
    if video_bitrate:
        cmd.extend(['-b:v', video_bitrate])
    if audio_bitrate:
        cmd.extend(['-b:a', audio_bitrate])
    if resolution:
        cmd.extend(['-s', resolution])
    
    cmd.append(output_path)
    
    try:
        if progress_callback:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            duration = probe(input_path).duration
            progress_pattern = re.compile(
                r'frame=\s*(\d+)\s+fps=\s*([\d.]+)\s+q=\s*([\d.]+)\s+size=\s*(\d+)kB\s+time=\s*([\d.]+)\s+bitrate=\s*([\d.]+kbits/s)\s+speed=\s*([\d.]+)x'
            )
            
            for line in process.stderr:
                match = progress_pattern.search(line)
                if match:
                    frame = int(match.group(1))
                    fps = float(match.group(2))
                    size = int(match.group(4))
                    time = float(match.group(5))
                    bitrate = float(match.group(6).replace('kbits/s', ''))
                    speed = float(match.group(7))
                    
                    progress = TranscodeProgress(
                        frame=frame,
                        fps=fps,
                        size=size,
                        time=time,
                        bitrate=bitrate,
                        speed=speed,
                        progress_percent=(time / duration * 100) if duration > 0 else 0
                    )
                    progress_callback(progress)
            
            process.wait()
            if process.returncode != 0:
                raise FFmpegExecutionError(f"FFmpeg transcode failed")
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
    except subprocess.CalledProcessError as e:
        raise FFmpegExecutionError(f"FFmpeg transcode failed: {e.stderr}")


def extract_audio(
    input_path: str,
    output_path: str,
    codec: str = 'libmp3lame',
    bitrate: str = '192k',
    sample_rate: Optional[str] = None,
) -> None:
    """Extract audio from video file.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output audio file
        codec: Audio codec to use
        bitrate: Audio bitrate
        sample_rate: Audio sample rate (e.g., '44100', '48000')
        
    Raises:
        FFmpegExecutionError: If extraction fails
    """
    cmd = [
        FFMPEG_PATH, '-y', '-i', input_path,
        '-vn', '-c:a', codec, '-b:a', bitrate
    ]
    
    if sample_rate:
        cmd.extend(['-ar', sample_rate])
    
    cmd.append(output_path)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise FFmpegExecutionError(f"Audio extraction failed: {e.stderr}")


def trim(
    input_path: str,
    output_path: str,
    start_time: str,
    duration: Optional[str] = None,
    end_time: Optional[str] = None,
) -> None:
    """Trim media file to a specific time range.
    
    Args:
        input_path: Path to input media file
        output_path: Path to output media file
        start_time: Start time (format: HH:MM:SS or seconds)
        duration: Duration to extract (format: HH:MM:SS or seconds)
        end_time: End time (alternative to duration)
        
    Raises:
        FFmpegExecutionError: If trim fails
    """
    cmd = [
        FFMPEG_PATH, '-y', '-i', input_path,
        '-ss', start_time
    ]
    
    if duration:
        cmd.extend(['-t', duration])
    elif end_time:
        cmd.extend(['-to', end_time])
    
    cmd.append(output_path)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise FFmpegExecutionError(f"Trim failed: {e.stderr}")


def get_duration(input_path: str) -> float:
    """Get duration of media file in seconds.
    
    Args:
        input_path: Path to media file
        
    Returns:
        Duration in seconds
    """
    info = probe(input_path)
    return info.duration


def get_resolution(input_path: str) -> Tuple[Optional[int], Optional[int]]:
    """Get video resolution.
    
    Args:
        input_path: Path to video file
        
    Returns:
        Tuple of (width, height)
    """
    info = probe(input_path)
    for stream in info.streams:
        if stream.codec_type == 'video':
            return stream.width, stream.height
    return None, None


def get_video_codec(input_path: str) -> Optional[str]:
    """Get video codec name.
    
    Args:
        input_path: Path to media file
        
    Returns:
        Video codec name or None
    """
    info = probe(input_path)
    for stream in info.streams:
        if stream.codec_type == 'video':
            return stream.codec_name
    return None


def get_audio_codec(input_path: str) -> Optional[str]:
    """Get audio codec name.
    
    Args:
        input_path: Path to media file
        
    Returns:
        Audio codec name or None
    """
    info = probe(input_path)
    for stream in info.streams:
        if stream.codec_type == 'audio':
            return stream.codec_name
    return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m ffmpeg <media_file_path>")
        sys.exit(1)
    
    try:
        info = probe(sys.argv[1])
        print(f"Media Info:")
        print(f"  Format: {info.format_name}")
        print(f"  Duration: {info.duration:.2f}s")
        print(f"  Size: {info.size_bytes} bytes")
        print(f"  Streams: {len(info.streams)}")
        for stream in info.streams:
            print(f"    [{stream.index}] {stream.codec_type}: {stream.codec_name}")
    except FFmpegError as e:
        print(f"Error: {e}")
        sys.exit(1)
