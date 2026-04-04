"""
Job queue system with retry logic for the Agentic TV Station.

This module provides a persistent job queue with exponential backoff retry mechanism
for handling failed jobs reliably.
"""

import json
import time
import uuid
import heapq
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Job:
    """Represents a job in the queue."""
    id: str
    task_type: str
    payload: Dict[str, Any]
    status: JobStatus
    created_at: str
    updated_at: str
    attempts: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    next_retry_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary."""
        data['status'] = JobStatus(data['status'])
        return cls(**data)


class JobQueue:
    """Persistent job queue with retry logic and exponential backoff."""
    
    def __init__(self, storage_path: str = "./job_queue.json"):
        self.storage_path = Path(storage_path)
        self.jobs: Dict[str, Job] = {}
        self.processing_handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        
        # Load existing jobs
        self._load_jobs()
    
    def register_handler(self, task_type: str, handler: Callable[[Dict[str, Any]], Any]):
        """Register a handler function for a specific task type."""
        self.processing_handlers[task_type] = handler
    
    def add_job(self, task_type: str, payload: Dict[str, Any], 
                max_attempts: int = 3) -> str:
        """Add a new job to the queue."""
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        job = Job(
            id=job_id,
            task_type=task_type,
            payload=payload,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            max_attempts=max_attempts
        )
        
        with self._lock:
            self.jobs[job_id] = job
            self._save_jobs()
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        with self._lock:
            return self.jobs.get(job_id)
    
    def complete_job(self, job_id: str, result: Any = None):
        """Mark a job as completed."""
        with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.updated_at = datetime.utcnow().isoformat()
                # Store result in payload for retrieval
                if result is not None:
                    job.payload['result'] = result
                self._save_jobs()
    
    def fail_job(self, job_id: str, error: str):
        """Mark a job as failed and schedule retry if applicable."""
        with self._lock:
            if job_id not in self.jobs:
                return
            
            job = self.jobs[job_id]
            job.attempts += 1
            job.last_error = error
            job.updated_at = datetime.utcnow().isoformat()
            
            if job.attempts < job.max_attempts:
                # Schedule retry with exponential backoff
                job.status = JobStatus.RETRYING
                delay = min(2 ** job.attempts, 300)  # Max 5 minutes
                job.next_retry_at = (datetime.utcnow() + timedelta(seconds=delay)).isoformat()
            else:
                # Max attempts reached
                job.status = JobStatus.FAILED
            
            self._save_jobs()
    
    def _should_process_job(self, job: Job) -> bool:
        """Check if a job should be processed now."""
        if job.status != JobStatus.PENDING and job.status != JobStatus.RETRYING:
            return False
        
        if job.status == JobStatus.RETRYING:
            if job.next_retry_at:
                retry_time = datetime.fromisoformat(job.next_retry_at)
                return datetime.utcnow() >= retry_time
            return False
        
        return True
    
    def _process_job(self, job: Job):
        """Process a single job."""
        handler = self.processing_handlers.get(job.task_type)
        if not handler:
            self.fail_job(job.id, f"No handler registered for task type: {job.task_type}")
            return
        
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.utcnow().isoformat()
        self._save_jobs()
        
        try:
            result = handler(job.payload)
            self.complete_job(job.id, result)
        except Exception as e:
            self.fail_job(job.id, str(e))
    
    def _worker_loop(self):
        """Main worker loop that processes jobs."""
        while not self._stop_worker.is_set():
            try:
                # Find next job to process
                job_to_process = None
                with self._lock:
                    for job in self.jobs.values():
                        if self._should_process_job(job):
                            job_to_process = job
                            break
                
                if job_to_process:
                    self._process_job(job_to_process)
                else:
                    # No jobs to process, sleep briefly
                    time.sleep(1)
                    
            except Exception as e:
                # Log error but continue worker loop
                print(f"Worker loop error: {e}")
                time.sleep(5)
    
    def start_worker(self):
        """Start the background worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        
        self._stop_worker.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
    
    def stop_worker(self):
        """Stop the background worker thread."""
        self._stop_worker.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics about the job queue."""
        with self._lock:
            stats = {
                'total': len(self.jobs),
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'retrying': 0
            }
            
            for job in self.jobs.values():
                stats[job.status.value] += 1
            
            return stats
    
    def _load_jobs(self):
        """Load jobs from persistent storage."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.jobs = {
                    job_id: Job.from_dict(job_data) 
                    for job_id, job_data in data.items()
                }
        except Exception as e:
            print(f"Failed to load jobs: {e}")
            self.jobs = {}
    
    def _save_jobs(self):
        """Save jobs to persistent storage."""
        try:
            # Create directory if it doesn't exist
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_path, 'w') as f:
                data = {
                    job_id: job.to_dict() 
                    for job_id, job in self.jobs.items()
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save jobs: {e}")


# Global job queue instance
job_queue = JobQueue()

def initialize_job_queue(storage_path: str = "./job_queue.json"):
    """Initialize the global job queue."""
    global job_queue
    job_queue = JobQueue(storage_path)
    return job_queue

def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    return job_queue
