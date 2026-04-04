
# Documentation: Agentic TV Station

## 1. Executive Summary

**Project Name:** Agentic TV Station  
**Status:** In Development  
**Repository:** https://github.com/cisco7507/agentic-tv-station  
**Local Path:** `/home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station`

An automated media processing pipeline for TV station operations. The system provides:
- Media file ingestion and validation
- FFmpeg-based media processing (transcoding, trimming, audio extraction)
- OpenAI Whisper transcription
- Intelligent clip extraction based on transcription
- Local storage management
- MCP (Model Context Protocol) server for AI tool integration
- Command-line interface for all operations

---

## 2. What This System Does

The Agentic TV Station is a comprehensive media processing pipeline that:

1. **Ingests media files** - Validates video/audio files for processing
2. **Processes media** - Transcodes, trims, extracts audio using FFmpeg
3. **Transcribes audio** - Uses OpenAI Whisper to convert speech to text
4. **Extracts clips** - Intelligently segments video based on transcription (silence detection, speaker changes)
5. **Manages storage** - Local file storage with upload/download/list operations
6. **Integrates with AI** - MCP server exposes all tools to AI assistants
7. **Provides CLI** - Command-line interface for all operations

---

## 3. Architecture Overview

### Non-Technical Explanation
This system acts as a "media factory" that:
- Takes video or audio files as input
- Converts them to different formats if needed
- Creates text transcripts of any speech
- Automatically finds good places to cut the video into shorter clips
- Stores all the resulting files neatly
- Can be controlled either from command line or by AI assistants

### Technical Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI / MCP Server                         │
├─────────────────────────────────────────────────────────────────┤
│  cli.py                    │        mcp_server.py              │
│  (command-line interface)  │   (AI tool integration)           │
└──────────────┬─────────────┴──────────────┬──────────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Core Processing Modules                     │
├─────────────┬─────────────┬──────────────┬─────────────────────┤
│  ingest.py │ ffmpeg.py   │ transcription│ clip_extractor.py  │
│             │ ffmpeg_wrapper             │                     │
├─────────────┼─────────────┼──────────────┼─────────────────────┤
│  storage.py │ webhook.py │              │                     │
└─────────────┴─────────────┴──────────────┴─────────────────────┘
```

### Data Flow
```
Input Media → Ingest (validate) → FFmpeg (process) → Transcription
                                                         │
                                                         ▼
                                              Clip Extractor
                                                         │
                                                         ▼
                                              Storage / Output
```

---

## 4. Project Structure

```
agentic-tv-station/
├── ingest.py              # Media file validation & metadata
├── ffmpeg.py              # Comprehensive FFmpeg utilities (425 lines)
├── ffmpeg_wrapper.py      # FFmpeg wrapper abstraction layer
├── transcription.py       # OpenAI Whisper transcription service
├── clip_extractor.py      # Clip extraction & boundary detection
├── storage.py             # Local storage management
├── webhook.py             # HTTP webhook client
├── cli.py                 # Command-line interface (228 lines)
├── mcp_server.py          # MCP server for AI integration (123 lines)
├── DOCUMENTATION.md       # This file
├── update_blocked.json    # Internal status (ignore)
├── .venv/                 # Python virtual environment
└── __pycache__/           # Python bytecode cache
```

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `ffmpeg.py` | 425 | Full FFmpeg wrapper with progress tracking |
| `cli.py` | 228 | Command-line interface |
| `clip_extractor.py` | 266 | Clip extraction with boundary detection |
| `mcp_server.py` | 123 | MCP server exposing all tools |
| `transcription.py` | 158 | Whisper API integration |
| `webhook.py` | 145 | HTTP webhook client |
| `ffmpeg_wrapper.py` | 213 | Simplified FFmpeg wrapper |
| `storage.py` | 113 | Local storage abstraction |
| `ingest.py` | 146 | Media file validation |

---

## 5. Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | Uses modern Python features |
| FFmpeg | Latest | For media processing |
| FFprobe | Latest | For media metadata |
| OpenAI API Key | - | For transcription (`OPENAI_API_KEY`) |

### Python Dependencies
Located in `.venv/`:
- `openai` - OpenAI API client
- `mcp` - Model Context Protocol
- `click` - CLI framework
- `anyio` - Async I/O
- `uvicorn` - ASGI server
- `httpx` - HTTP client
- `python-dotenv` - Environment variables

### System Dependencies
```bash
# Install FFmpeg
# Ubuntu/Debian:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Verify installation:
ffmpeg -version
ffprobe -version
```

---

## 6. Installation and Setup

### Step 1: Ensure Prerequisites
```bash
# Check Python
python3 --version  # Should be 3.12+

# Check FFmpeg
ffmpeg -version
```

### Step 2: Navigate to Project
```bash
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station
```

### Step 3: Set Environment Variables
```bash
# Required for transcription
export OPENAI_API_KEY="your-api-key-here"

# Optional
export OPENAI_BASE_URL="https://api.openai.com/v1"  # For compatible APIs
export STORAGE_PATH="/home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/storage"  # Local storage directory
export TEMP="/tmp"  # Temp directory
```

### Step 4: Verify Installation
```bash
# Test basic import
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station
python3 -c "from ingest import ingest_file; print('OK')"
```

---

## 7. Configuration / Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for Whisper transcription | `sk-...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Alternative API endpoint |
| `STORAGE_PATH` | `/home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/storage` | Local storage directory |
| `TEMP` | `/tmp` | Temp file directory |

### Configuration File
Create a `.env` file in the project root:
```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
STORAGE_PATH=./storage
```

---

## 8. How to Run the System

### Quick Start (CLI)

#### Ingest a media file:
```bash
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py ingest video.mp4
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py ingest video.mp4 --format-info
```

#### Transcribe media:
```bash
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py transcribe video.mp4 --language en --output transcript.txt
```

#### Full processing pipeline:
```bash
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py process video.mp4 --output-dir ./output --extract-clips
```

#### Storage operations:
```bash
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py storage upload video.mp4
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py storage download video.mp4 ./downloads/
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py storage list
```

### MCP Server (AI Integration)

Start the MCP server for AI tool integration:
```bash
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/mcp_server.py --host 127.0.0.1 --port 5000
```

The MCP server exposes these tools to AI assistants:
- `ingest_media` - Validate and ingest media files
- `get_format_info` - Get detailed media file information
- `transcribe_media` - Transcribe audio from media files
- `extract_audio` - Extract audio track from video
- `get_media_duration` - Get duration in seconds
- `get_video_info` - Get video stream info (resolution, codec, fps)
- `trim_media` - Trim media to time range
- `find_clip_boundaries` - Find natural clip boundaries
- `extract_clip` - Extract clip from video
- `list_supported_formats` - List supported formats

---

## 9. How to Test the System

### Unit Tests (Manual)

#### Test Ingest:
```python
from ingest import validate_file, get_format_info, IngestError

try:
    media = validate_file("/path/to/video.mp4")
    print(f"Type: {media.media_type}, Format: {media.format}")
except IngestError as e:
    print(f"Error: {e}")
```

#### Test FFmpeg:
```python
from ffmpeg_wrapper import FFmpegWrapper

fw = FFmpegWrapper()
duration = fw.get_duration("video.mp4")
info = fw.get_video_info("video.mp4")
print(f"Duration: {duration}s, Resolution: {info['width']}x{info['height']}")
```

#### Test Transcription:
```python
from transcription import TranscriptionService

service = TranscriptionService()
result = service.transcribe("audio.mp3", language="en")
print(result["text"])
```

#### Test Clip Extraction:
```python
from clip_extractor import ClipBoundaryDetector, Transcription

# Load transcription
transcription = Transcription.from_json("transcript.json")

# Find boundaries
detector = ClipBoundaryDetector(min_clip_duration=5.0, max_clip_duration=120.0)
boundaries = detector.find_boundaries(transcription)
print(f"Found {len(boundaries)} clip boundaries")
```

### Integration Test
```bash
# Full pipeline test
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py process test_video.mp4 --output-dir ./test_output --extract-clips
```

---

## 10. Feature Documentation

### Media Ingest (`ingest.py`)

Validates and extracts metadata from media files.

**Supported Video Formats:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`

**Supported Audio Formats:** `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a`, `.wma`

**Key Functions:**
- `validate_file(path)` - Validate file exists, is readable, format supported
- `ingest_file(path)` - Main ingest function
- `stream_file_chunks(path)` - Generator for large file streaming (1MB chunks)
- `get_format_info(path)` - Get detailed metadata

**Classes:**
- `MediaFile` - Represents a media file
- `IngestError`, `FileNotFoundError`, `FileNotReadableError`, `UnsupportedFormatError`

### FFmpeg Processing (`ffmpeg.py`, `ffmpeg_wrapper.py`)

Two FFmpeg wrappers with different capabilities:

**Simple Wrapper (`ffmpeg_wrapper.py`):**
- `probe(input_path)` - Get full media metadata
- `get_duration(input_path)` - Duration in seconds
- `get_video_info(input_path)` - Resolution, codec, fps
- `get_audio_info(input_path)` - Audio codec, sample rate, channels
- `extract_audio(input_path, output_path)` - Extract audio track
- `trim(input_path, output_path, start, duration)` - Trim media
- `transcode(input_path, output_path, ...)` - Transcode with options

**Full Wrapper (`ffmpeg.py`):**
- `find_ffmpeg()` - Locate FFmpeg executables
- `MediaInfo` dataclass - Full media file info
- `TranscodeProgress` dataclass - Progress tracking
- Advanced transcoding with progress callbacks

### Transcription (`transcription.py`)

OpenAI Whisper transcription service.

**Key Functions:**
- `transcribe(audio_path, language, prompt, ...)` - Transcribe audio file
- `transcribe_video(video_path, ...)` - Transcribe directly from video (auto-extracts audio)

**Configuration:**
- Model: `whisper-1` (default)
- Languages: Any Whisper-supported language code
- Response formats: `json`, `text`, `srt`, `vtt`

### Clip Extraction (`clip_extractor.py`)

Intelligent clip extraction based on transcription.

**Key Classes:**
- `TranscriptionSegment` - Timestamped text segment
- `Transcription` - Full transcription with segments
- `ClipBoundaryDetector` - Finds natural clip boundaries
- `ClipExtractor` - Extracts clips from video

**Boundary Detection:**
- Silence gaps (configurable threshold, default 2 seconds)
- Speaker changes
- Maximum clip duration (default 120 seconds)

### Storage (`storage.py`)

Local file storage abstraction.

**Key Functions:**
- `upload(local_path, key)` - Upload file to storage
- `download(key, local_path)` - Download from storage
- `exists(key)` - Check if file exists
- `delete(key)` - Delete file
- `list(prefix)` - List storage contents

### Webhook Client (`webhook.py`)

HTTP webhook client for external integrations.

**Key Functions:**
- `post(url, data)` - Send POST request
- `get(url, params)` - Send GET request
- `put(url, data)` - Send PUT request

---

## 11. API / Integration Documentation

### MCP Server Tools

The MCP server exposes all functionality to AI assistants. See Section 8 for usage.

### CLI Commands

| Command | Description |
|---------|-------------|
| `ingest <file>` | Validate media file |
| `transcribe <file>` | Transcribe media |
| `process <file>` | Full pipeline |
| `storage upload <file>` | Upload to storage |
| `storage download <key>` | Download from storage |
| `storage list` | List storage contents |

---

## 12. Database

**No database** - Uses local file storage.

Future considerations:
- SQLite for metadata tracking
- PostgreSQL for scheduling/queue

---

## 13. Deployment

### Local Development
```bash
# Navigate to the project
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station

# Activate virtual environment
source /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/.venv/bin/activate

# Run CLI
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py process video.mp4
```

### MCP Server Deployment
```bash
# Production MCP server
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/mcp_server.py --host 0.0.0.0 --port 5000
```

### Docker (Future)
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python3", "cli.py"]
```

---

## 14. Troubleshooting Guide

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Unsupported format: .xyz` | File extension not supported | Use supported format |
| `File not found: /path` | File doesn't exist | Check path is correct |
| `ffmpeg not found` | FFmpeg not installed | Install FFmpeg |
| `API key required` | OPENAI_API_KEY not set | Set environment variable |
| `Transcription failed` | API error or network issue | Check API key and connectivity |

### Debug Steps

1. **Check FFmpeg installation:**
   ```bash
   ffmpeg -version
   ffprobe -version
   ```

2. **Verify environment:**
   ```bash
   echo $OPENAI_API_KEY
   ```

3. **Test imports:**
   ```python
   python3 -c "from ffmpeg_wrapper import FFmpegWrapper; print('OK')"
   ```

4. **Run with verbose logging:**
   ```bash
   cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station
   python3 -u /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py process video.mp4 --output-dir ./output 2>&1
   ```

---

## 15. Maintenance Guide

### Routine Tasks

- **Clean temp files:** Clear temp directory if storage fills up
- **Update dependencies:** `pip install -U -r requirements.txt`
- **Monitor storage:** Check `/home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/storage` directory size

### Code Updates

All modules are self-contained. Changes take effect immediately on next run.

### Adding New Features

1. Add to relevant module (`transcription.py`, `ffmpeg_wrapper.py`, etc.)
2. Update CLI in `cli.py` if needed
3. Add MCP tool in `mcp_server.py` if needed
4. Update this documentation

---

## 16. Risks, Gaps, and Unknowns

### Known Gaps

1. **No database** - Metadata tracking is manual
2. **No tests** - No automated test suite
3. **No CI/CD** - No automated build/deployment
4. **Local storage only** - No cloud storage integration
5. **No authentication** - MCP server has no auth
6. **No rate limiting** - API calls are unbounded
7. **No queue system** - Processing is synchronous

### Security Considerations

1. **API keys in environment** - Don't commit to version control
2. **No input validation** - Could be vulnerable to path traversal
3. **No size limits** - Large files could cause issues

### Open Questions

- What cloud storage will be used (S3, GCS, etc.)?
- What scheduling system for automated processing?
- What monitoring/alerting for failures?
- Will there be a web UI?

---

## 17. Recommended Next Steps

### Immediate
1. Add test suite (pytest)
2. Add input validation and sanitization
3. Add authentication to MCP server

### Short-term
4. Implement cloud storage integration
5. Add queue system for async processing
6. Set up basic CI/CD

### Long-term
7. Build web UI
8. Add monitoring/alerting
9. Implement scheduling for automated workflows

---

## Quick Start Guide (Non-Technical)

Welcome! Here's how to get started:

### Step 1: Get Ready
You need:
- Python 3.12 or higher
- FFmpeg (media processing tool)
- An OpenAI API key (for transcription)

### Step 2: Set Up
```bash
# Navigate to the project folder
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station

# Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"
```

### Step 3: Try It Out

**Process a video:**
```bash
cd /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station
python3 /home/gsp/.paperclip/instances/default/projects/eb13f383-9e2c-4711-8a39-b652b63765a9/8a70604c-699b-4d90-9ea6-536c65658aa5/agentic-tv-station/cli.py process your_video.mp4 --output-dir ./output
```

This will:
1. Check your video file
2. Extract the audio
3. Convert speech to text
4. Save everything to the `./output` folder

**That's it!** The system handles all the technical details.

---

## Glossary

| Term | Plain English Definition |
|------|-------------------------|
| Ingest | To take in and validate a file |
| Transcode | Convert media from one format to another |
| Trim | Cut a video to a specific time range |
| Extract audio | Pull the sound track out of a video |
| Transcription | Convert speech to written text |
| Whisper | OpenAI's speech-to-text AI |
| Clip | A short segment cut from a video |
| Boundary | A natural place to cut a video (silence, speaker change) |
| MCP | Protocol for AI assistants to use tools |
| Chunk | A piece of a large file |
| Codec | The way a video/audio file is encoded |

---

*Document updated by Technical Writer agent on 2026-04-04*
*Issue: [NEU-16](/NEU/issues/NEU-16)*
