"""
MCP server with retry logic for reliable tool execution.
This enhances the original mcp_server.py with retry mechanisms.
"""

import anyio
import click
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from ingest import ingest_file, get_format_info, SUPPORTED_VIDEO_FORMATS, SUPPORTED_AUDIO_FORMATS
from ffmpeg_wrapper import FFmpegWrapper
from transcription import TranscriptionService
from clip_extractor import ClipExtractor, ClipBoundaryDetector, load_transcription
from utils.retry_tool import retry_with_backoff
from utils.job_queue import job_queue, Job

import logging
import json
from pathlib import Path
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("agentic-tv-station")

ffmpeg = FFmpegWrapper()
clip_extractor = ClipExtractor(ffmpeg)
boundary_detector = ClipBoundaryDetector()


# Register job handlers
def handle_transcribe_media(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for transcribe_media jobs."""
    service = TranscriptionService()
    result = service.transcribe(payload['file_path'], language=payload.get('language'))
    if payload.get('output_path'):
        Path(payload['output_path']).write_text(json.dumps(result))
    return result

def handle_extract_audio(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for extract_audio jobs."""
    result = ffmpeg.extract_audio(payload['input_path'], payload['output_path'])
    return result

def handle_get_media_duration(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for get_media_duration jobs."""
    duration = ffmpeg.get_duration(payload['file_path'])
    return {"duration_seconds": duration}

def handle_get_video_info(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for get_video_info jobs."""
    info = ffmpeg.get_video_info(payload['file_path'])
    return info

def handle_trim_media(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for trim_media jobs."""
    result = ffmpeg.trim(payload['input_path'], payload['output_path'], 
                        payload['start_seconds'], payload['duration_seconds'])
    return result

def handle_find_clip_boundaries(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for find_clip_boundaries jobs."""
    transcription = load_transcription(payload['transcription_path'])
    boundary_detector.min_clip_duration = payload.get('min_duration', 5.0)
    boundary_detector.max_clip_duration = payload.get('max_duration', 120.0)
    boundary_detector.silence_threshold = payload.get('silence_threshold', 2.0)
    boundaries = boundary_detector.find_boundaries(transcription)
    return [
        {"start": s, "end": e, "duration": e - s}
        for s, e in boundaries
    ]

def handle_extract_clip(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for extract_clip jobs."""
    result = clip_extractor.extract_clip(
        payload['input_path'], 
        payload['output_path'], 
        payload['start_seconds'], 
        payload['end_seconds']
    )
    return result

def handle_list_supported_formats(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for list_supported_formats jobs."""
    return {
        "video": list(SUPPORTED_VIDEO_FORMATS),
        "audio": list(SUPPORTED_AUDIO_FORMATS),
    }

# Register all handlers
job_queue.register_handler("transcribe_media", handle_transcribe_media)
job_queue.register_handler("extract_audio", handle_extract_audio)
job_queue.register_handler("get_media_duration", handle_get_media_duration)
job_queue.register_handler("get_video_info", handle_get_video_info)
job_queue.register_handler("trim_media", handle_trim_media)
job_queue.register_handler("find_clip_boundaries", handle_find_clip_boundaries)
job_queue.register_handler("extract_clip", handle_extract_clip)
job_queue.register_handler("list_supported_formats", handle_list_supported_formats)

# Start the job queue worker
job_queue.start_worker()


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
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
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def get_format_info(file_path: str) -> str:
    """Get detailed format information about a media file"""
    info = get_format_info(file_path)
    return json.dumps(info)


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def transcribe_media(file_path: str, language: str = None, output_path: str = None) -> str:
    """Transcribe audio from a media file - processed via job queue for reliability"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="transcribe_media",
        payload={
            "file_path": file_path,
            "language": language,
            "output_path": output_path
        },
        max_attempts=3
    )
    
    # Wait for completion (in a real implementation, this might be async)
    # For now, we'll poll briefly - in production this would use callbacks/webhooks
    import time
    max_wait = 30  # Maximum wait time in seconds
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Transcription failed: {job.last_error}")
    else:
        raise Exception("Transcription timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def extract_audio(input_path: str, output_path: str) -> str:
    """Extract audio track from a video file - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="extract_audio",
        payload={
            "input_path": input_path,
            "output_path": output_path
        },
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 30
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Audio extraction failed: {job.last_error}")
    else:
        raise Exception("Audio extraction timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def get_media_duration(file_path: str) -> str:
    """Get the duration of a media file in seconds - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="get_media_duration",
        payload={
            "file_path": file_path
        },
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 10
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Media duration failed: {job.last_error}")
    else:
        raise Exception("Media duration timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def get_video_info(file_path: str) -> str:
    """Get video stream information (resolution, codec, fps) - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="get_video_info",
        payload={
            "file_path": file_path
        },
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 10
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Video info failed: {job.last_error}")
    else:
        raise Exception("Video info timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def trim_media(input_path: str, output_path: str, start_seconds: float, duration_seconds: float) -> str:
    """Trim media file to a specific time range - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="trim_media",
        payload={
            "input_path": input_path,
            "output_path": output_path,
            "start_seconds": start_seconds,
            "duration_seconds": duration_seconds
        },
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 30
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Trim failed: {job.last_error}")
    else:
        raise Exception("Trim timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def find_clip_boundaries(transcription_path: str, min_duration: float = 5.0, max_duration: float = 120.0, silence_threshold: float = 2.0) -> str:
    """Find natural clip boundaries in a transcription - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="find_clip_boundaries",
        payload={
            "transcription_path": transcription_path,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "silence_threshold": silence_threshold
        },
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 30
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', []))
    elif job and job.status == "failed":
        raise Exception(f"Finding clip boundaries failed: {job.last_error}")
    else:
        raise Exception("Finding clip boundaries timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def extract_clip(input_path: str, output_path: str, start_seconds: float, end_seconds: float) -> str:
    """Extract a clip from video based on timestamps - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="extract_clip",
        payload={
            "input_path": input_path,
            "output_path": output_path,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds
        },
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 30
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Clip extraction failed: {job.last_error}")
    else:
        raise Exception("Clip extraction timeout")


@mcp.tool()
@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=10.0)
def list_supported_formats() -> str:
    """List all supported video and audio formats - processed via job queue"""
    # Add job to queue for reliable execution
    job_id = job_queue.add_job(
        task_type="list_supported_formats",
        payload={},
        max_attempts=3
    )
    
    # Wait for completion
    import time
    max_wait = 5
    wait_time = 0
    while wait_time < max_wait:
        job = job_queue.get_job(job_id)
        if job and job.status in ["completed", "failed"]:
            break
        time.sleep(1)
        wait_time += 1
    
    job = job_queue.get_job(job_id)
    if job and job.status == "completed":
        return json.dumps(job.payload.get('result', {}))
    elif job and job.status == "failed":
        raise Exception(f"Listing supported formats failed: {job.last_error}")
    else:
        raise Exception("Listing supported formats timeout")


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, help="Port to bind to")
def main(host: str, port: int):
    """Run the Agentic TV Station MCP Server with retry logic."""
    try:
        anyio.run(mcp.run_stdio_async)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server...")
        job_queue.stop_worker()
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        job_queue.stop_worker()
        raise


if __name__ == "__main__":
    main()
