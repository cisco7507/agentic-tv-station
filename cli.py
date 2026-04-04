#!/usr/bin/env python3
"""CLI for the Agentic TV Station media pipeline."""

import argparse
import logging
import sys
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Agentic TV Station - Media Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ingest video.mp4              - Ingest a video file
  %(prog)s transcribe video.mp4          - Transcribe video audio
  %(prog)s process video.mp4             - Full pipeline (ingest + transcribe)
  %(prog)s storage upload video.mp4      - Upload to storage
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a media file")
    ingest_parser.add_argument("file", help="Path to media file")
    ingest_parser.add_argument("--format-info", action="store_true", help="Show format info")
    
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe media file")
    transcribe_parser.add_argument("file", help="Path to media file")
    transcribe_parser.add_argument("--language", help="Language code (e.g., en)")
    transcribe_parser.add_argument("--output", "-o", help="Output file for transcript")
    
    process_parser = subparsers.add_parser("process", help="Run full pipeline")
    process_parser.add_argument("file", help="Path to media file")
    process_parser.add_argument("--output-dir", "-o", default="./output", help="Output directory")
    process_parser.add_argument("--language", help="Language code")
    process_parser.add_argument("--extract-clips", action="store_true", help="Extract clips from transcription")
    process_parser.add_argument("--min-clip-duration", type=float, default=5.0, help="Min clip duration")
    process_parser.add_argument("--max-clip-duration", type=float, default=120.0, help="Max clip duration")
    
    storage_parser = subparsers.add_parser("storage", help="Storage operations")
    storage_sub = storage_parser.add_subparsers(dest="storage_command")
    
    upload_parser = storage_sub.add_parser("upload", help="Upload file to storage")
    upload_parser.add_argument("file", help="Path to file")
    upload_parser.add_argument("--key", help="Storage key")
    
    download_parser = storage_sub.add_parser("download", help="Download file from storage")
    download_parser.add_argument("key", help="Storage key")
    download_parser.add_argument("dest", help="Destination path")
    
    list_parser = storage_sub.add_parser("list", help="List storage contents")
    list_parser.add_argument("--prefix", help="Prefix filter")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        if args.command == "ingest":
            from ingest import ingest_file, get_format_info, IngestError
            try:
                media = ingest_file(args.file)
                logger.info(f"Ingested: {media.path}")
                if args.format_info:
                    info = get_format_info(args.file)
                    print(f"Format info: {info}")
            except IngestError as e:
                logger.error(f"Ingest failed: {e}")
                return 1
                
        elif args.command == "transcribe":
            from transcription import TranscriptionService, TranscriptionError
            try:
                service = TranscriptionService()
                result = service.transcribe(
                    args.file,
                    language=args.language
                )
                logger.info(f"Transcription complete: {result['text'][:100]}...")
                if args.output:
                    Path(args.output).write_text(result["text"])
                    logger.info(f"Saved to {args.output}")
            except TranscriptionError as e:
                logger.error(f"Transcription failed: {e}")
                return 1
                
        elif args.command == "process":
            from ingest import ingest_file, IngestError
            from ffmpeg_wrapper import FFmpegWrapper, FFmpegError
            from transcription import TranscriptionService, TranscriptionError
            from storage import Storage
            
            os.makedirs(args.output_dir, exist_ok=True)
            
            logger.info(f"Processing: {args.file}")
            
            try:
                media = ingest_file(args.file)
                logger.info(f"Ingested: {media}")
            except IngestError as e:
                logger.error(f"Ingest failed: {e}")
                return 1
            
            if media.media_type == "video":
                logger.info("Extracting audio from video...")
                fw = FFmpegWrapper()
                audio_path = os.path.join(args.output_dir, f"{Path(args.file).stem}_audio.mp3")
                try:
                    fw.extract_audio(args.file, audio_path)
                    logger.info(f"Audio extracted to: {audio_path}")
                except FFmpegError as e:
                    logger.error(f"Audio extraction failed: {e}")
                    return 1
                    
                logger.info("Transcribing audio...")
                try:
                    service = TranscriptionService()
                    result = service.transcribe(audio_path, language=args.language)
                    transcript_path = os.path.join(args.output_dir, "transcript.txt")
                    Path(transcript_path).write_text(result["text"])
                    logger.info(f"Transcript saved to: {transcript_path}")
                except TranscriptionError as e:
                    logger.error(f"Transcription failed: {e}")
                    return 1
            else:
                logger.info("Transcribing audio file...")
                try:
                    service = TranscriptionService()
                    result = service.transcribe(args.file, language=args.language)
                    transcript_path = os.path.join(args.output_dir, "transcript.txt")
                    Path(transcript_path).write_text(result["text"])
                    logger.info(f"Transcript saved to: {transcript_path}")
                except TranscriptionError as e:
                    logger.error(f"Transcription failed: {e}")
                    return 1
            
            logger.info("Pipeline complete!")
            
            if args.extract_clips:
                from clip_extractor import ClipExtractor, ClipBoundaryDetector, Transcription, TranscriptionSegment
                from ffmpeg_wrapper import FFmpegWrapper
                import json
                
                logger.info("Extracting clips from transcription...")
                
                detector = ClipBoundaryDetector(
                    min_clip_duration=args.min_clip_duration,
                    max_clip_duration=args.max_clip_duration,
                )
                
                transcription_obj = Transcription.from_whisper(result)
                clip_suggestions = detector.suggest_clips(transcription_obj)
                
                if not clip_suggestions:
                    logger.warning("No clip boundaries detected, extracting full file")
                    clip_suggestions = [{"start": 0.0, "end": 300.0}]
                
                fw = FFmpegWrapper()
                ce = ClipExtractor(fw)
                
                clip_results = ce.extract_clips(
                    args.file,
                    args.output_dir,
                    clip_suggestions
                )
                
                for i, clip in enumerate(clip_results):
                    logger.info(f"Extracted clip {i+1}: {clip['output_path']} ({clip['duration']:.1f}s)")
                
                logger.info(f"Extracted {len(clip_results)} clips")
            
        elif args.command == "storage":
            from storage import Storage, StorageError
            
            storage = Storage()
            
            if args.storage_command == "upload":
                key = args.key or Path(args.file).name
                try:
                    result = storage.upload(args.file, key)
                    logger.info(f"Uploaded: {result}")
                except StorageError as e:
                    logger.error(f"Upload failed: {e}")
                    return 1
                    
            elif args.storage_command == "download":
                try:
                    result = storage.download(args.key, args.dest)
                    logger.info(f"Downloaded: {result}")
                except StorageError as e:
                    logger.error(f"Download failed: {e}")
                    return 1
                    
            elif args.storage_command == "list":
                try:
                    files = storage.list(args.prefix or "")
                    for f in files:
                        print(f"  {f['key']} ({f['size']} bytes)")
                except StorageError as e:
                    logger.error(f"List failed: {e}")
                    return 1
            else:
                storage_parser.print_help()
                return 1
        else:
            parser.print_help()
            return 1
            
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
