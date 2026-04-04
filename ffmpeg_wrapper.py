import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Base exception for FFmpeg operations."""
    pass


class FFmpegProbeError(FFmpegError):
    """Raised when ffprobe fails."""
    pass


class FFmpegTranscodeError(FFmpegError):
    """Raised when ffmpeg transcode fails."""
    pass


class FFmpegWrapper:
    """FFmpeg wrapper abstraction layer for media operations."""
    
    def __init__(self, binary_path: str = "ffmpeg", probe_path: str = "ffprobe"):
        self.binary_path = binary_path
        self.probe_path = probe_path
    
    def probe(self, input_path: str) -> dict:
        """Get media file metadata using ffprobe."""
        cmd = [
            self.probe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            input_path
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise FFmpegProbeError(f"ffprobe failed: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise FFmpegProbeError(f"Failed to parse ffprobe output: {e}") from e
    
    def get_format(self, input_path: str) -> str:
        """Get the format/container name of a media file."""
        data = self.probe(input_path)
        return data.get("format", {}).get("format_name", "unknown")
    
    def get_duration(self, input_path: str) -> float:
        """Get the duration of a media file in seconds."""
        data = self.probe(input_path)
        duration = data.get("format", {}).get("duration")
        return float(duration) if duration else 0.0
    
    def get_video_info(self, input_path: str) -> Optional[dict]:
        """Get video stream information."""
        data = self.probe(input_path)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                return {
                    "codec": stream.get("codec_name"),
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "fps": self._parse_fps(stream.get("r_frame_rate")),
                }
        return None
    
    def get_audio_info(self, input_path: str) -> Optional[dict]:
        """Get audio stream information."""
        data = self.probe(input_path)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                return {
                    "codec": stream.get("codec_name"),
                    "sample_rate": stream.get("sample_rate"),
                    "channels": stream.get("channels"),
                    "bit_rate": stream.get("bit_rate"),
                }
        return None
    
    def _parse_fps(self, fps_str: Optional[str]) -> float:
        """Parse FPS from fraction string like '30/1' or '30000/1001'."""
        if not fps_str:
            return 0.0
        if "/" in fps_str:
            num, denom = fps_str.split("/")
            return float(num) / float(denom)
        return float(fps_str)
    
    def transcode(
        self,
        input_path: str,
        output_path: str,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        video_bitrate: Optional[str] = None,
        audio_bitrate: Optional[str] = None,
        preset: str = "medium",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Transcode media file with specified options."""
        cmd = [self.binary_path, "-y", "-i", input_path]
        
        if video_codec:
            cmd.extend(["-c:v", video_codec])
        if audio_codec:
            cmd.extend(["-c:a", audio_codec])
        if video_bitrate:
            cmd.extend(["-b:v", video_bitrate])
        if audio_bitrate:
            cmd.extend(["-b:a", audio_bitrate])
        if preset:
            cmd.extend(["-preset", preset])
        
        cmd.append(output_path)
        
        try:
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            duration = self.get_duration(input_path)
            
            if process.stderr:
                for line in process.stderr:
                    if progress_callback and duration > 0:
                        time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                        if time_match:
                            hours, minutes, seconds = time_match.groups()
                            current_time = (
                                int(hours) * 3600 +
                                int(minutes) * 60 +
                                float(seconds)
                            )
                            progress = (current_time / duration) * 100
                            progress_callback(progress)
            
            process.wait()
            
            if process.returncode != 0:
                raise FFmpegTranscodeError(f"ffmpeg exited with code {process.returncode}")
            
            return {
                "success": True,
                "input": input_path,
                "output": output_path,
            }
            
        except FileNotFoundError:
            raise FFmpegError(f"ffmpeg not found at {self.binary_path}") from None
    
    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        codec: str = "libmp3lame",
        bitrate: str = "192k",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Extract audio track from video file."""
        cmd = [
            self.binary_path, "-y",
            "-i", input_path,
            "-vn",
            "-c:a", codec,
            "-b:a", bitrate,
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            raise FFmpegTranscodeError(f"Audio extraction failed: {e.stderr}") from e
    
    def trim(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        duration_seconds: Optional[float] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Trim media file to specified time range."""
        cmd = [
            self.binary_path, "-y",
            "-i", input_path,
            "-ss", str(start_seconds),
        ]
        
        if duration_seconds:
            cmd.extend(["-t", str(duration_seconds)])
        
        cmd.append(output_path)
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return {"success": True, "output": output_path}
        except subprocess.CalledProcessError as e:
            raise FFmpegTranscodeError(f"Trim failed: {e.stderr}") from e
