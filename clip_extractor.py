import json
import logging
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class ClipExtractionError(Exception):
    """Raised when clip extraction fails."""
    pass


class TranscriptionSegment:
    """Represents a segment of transcription with timestamps."""
    
    def __init__(self, start: float, end: float, text: str, speaker: Optional[str] = None):
        self.start = start
        self.end = end
        self.text = text
        self.speaker = speaker
    
    @classmethod
    def from_dict(cls, data: dict) -> "TranscriptionSegment":
        return cls(
            start=float(data.get("start", 0)),
            end=float(data.get("end", 0)),
            text=data.get("text", ""),
            speaker=data.get("speaker")
        )
    
    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker
        }
    
    @property
    def duration(self) -> float:
        return self.end - self.start


class Transcription:
    """Represents a full transcription with timestamped segments."""
    
    def __init__(self, segments: list[TranscriptionSegment], metadata: Optional[dict] = None):
        self.segments = segments
        self.metadata = metadata or {}
    
    @classmethod
    def from_json(cls, json_path: str) -> "Transcription":
        with open(json_path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Transcription":
        segments = [TranscriptionSegment.from_dict(s) for s in data.get("segments", [])]
        return cls(segments, data.get("metadata", {}))
    
    @classmethod
    def from_whisper(cls, whisper_output: dict) -> "Transcription":
        """Create Transcription from Whisper JSON output."""
        segments = []
        for segment in whisper_output.get("segments", []):
            segments.append(TranscriptionSegment(
                start=segment.get("start", 0),
                end=segment.get("end", 0),
                text=segment.get("text", "").strip()
            ))
        return cls(segments, {"model": whisper_output.get("language", "unknown")})
    
    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "metadata": self.metadata
        }
    
    @property
    def duration(self) -> float:
        if not self.segments:
            return 0.0
        return self.segments[-1].end
    
    def get_segment_at(self, timestamp: float) -> Optional[TranscriptionSegment]:
        for segment in self.segments:
            if segment.start <= timestamp <= segment.end:
                return segment
        return None
    
    def get_segments_in_range(self, start: float, end: float) -> list[TranscriptionSegment]:
        return [
            s for s in self.segments
            if s.end >= start and s.start <= end
        ]


class ClipBoundaryDetector:
    """Detects natural clip boundaries in transcription."""
    
    def __init__(
        self,
        min_clip_duration: float = 5.0,
        max_clip_duration: float = 120.0,
        silence_threshold: float = 2.0,
    ):
        self.min_clip_duration = min_clip_duration
        self.max_clip_duration = max_clip_duration
        self.silence_threshold = silence_threshold
    
    def find_boundaries(self, transcription: Transcription) -> list[tuple[float, float]]:
        """Find natural clip boundaries based on silence and segment changes."""
        boundaries = []
        clip_start = 0.0
        
        for i, segment in enumerate(transcription.segments):
            gap_before = segment.start - (transcription.segments[i-1].end if i > 0 else 0)
            
            is_silence_gap = gap_before >= self.silence_threshold
            is_new_speaker = (
                i > 0 and 
                transcription.segments[i-1].speaker != segment.speaker and
                segment.speaker is not None
            )
            
            clip_end = segment.start
            clip_duration = clip_end - clip_start
            
            should_split = (
                is_silence_gap or 
                is_new_speaker or
                clip_duration >= self.max_clip_duration
            )
            
            if should_split and clip_duration >= self.min_clip_duration:
                boundaries.append((clip_start, clip_end))
                clip_start = segment.start
        
        final_clip_end = transcription.duration
        final_duration = final_clip_end - clip_start
        if final_duration >= self.min_clip_duration:
            boundaries.append((clip_start, final_clip_end))
        
        return boundaries
    
    def suggest_clips(
        self,
        transcription: Transcription,
        target_duration: Optional[float] = None,
    ) -> list[dict]:
        """Suggest clips with optional target duration."""
        if target_duration:
            return self._suggest_fixed_duration_clips(transcription, target_duration)
        
        boundaries = self.find_boundaries(transcription)
        return [
            {"start": start, "end": end, "duration": end - start}
            for start, end in boundaries
        ]
    
    def _suggest_fixed_duration_clips(
        self,
        transcription: Transcription,
        target_duration: float,
    ) -> list[dict]:
        """Suggest clips of fixed duration, splitting at segment boundaries."""
        clips = []
        current_start = 0.0
        
        while current_start < transcription.duration:
            current_end = min(current_start + target_duration, transcription.duration)
            
            for segment in transcription.segments:
                if segment.start >= current_end:
                    break
                if segment.end > current_end:
                    current_end = segment.end
            
            clips.append({
                "start": current_start,
                "end": current_end,
                "duration": current_end - current_start
            })
            current_start = current_end
        
        return clips


class ClipExtractor:
    """Extracts clips from video based on transcription timestamps."""
    
    def __init__(self, ffmpeg_wrapper):
        self.ffmpeg = ffmpeg_wrapper
    
    def extract_clip(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        end_seconds: float,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Extract a clip from the input video."""
        duration = end_seconds - start_seconds
        
        if duration <= 0:
            raise ClipExtractionError(f"Invalid clip duration: {duration}")
        
        result = self.ffmpeg.trim(
            input_path=input_path,
            output_path=output_path,
            start_seconds=start_seconds,
            duration_seconds=duration,
            progress_callback=progress_callback,
        )
        
        return {
            **result,
            "start": start_seconds,
            "end": end_seconds,
            "duration": duration,
        }
    
    def extract_clips(
        self,
        input_path: str,
        output_dir: str,
        clips: list[dict],
        output_format: str = "mp4",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> list[dict]:
        """Extract multiple clips from the input video."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = []
        for i, clip in enumerate(clips):
            output_file = output_path / f"clip_{i+1}.{output_format}"
            
            def progress_wrapper(progress: float):
                if progress_callback:
                    clip_progress = (i + progress / 100) / len(clips) * 100
                    progress_callback(clip_progress)
            
            result = self.extract_clip(
                input_path=input_path,
                output_path=str(output_file),
                start_seconds=clip["start"],
                end_seconds=clip["end"],
                progress_callback=progress_wrapper,
            )
            results.append(result)
        
        return results


def load_transcription(path: str) -> Transcription:
    """Load transcription from JSON file."""
    ext = Path(path).suffix.lower()
    
    if ext == ".json":
        return Transcription.from_json(path)
    
    raise ClipExtractionError(f"Unsupported transcription format: {ext}")
