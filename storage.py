import os
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class StorageUploadError(StorageError):
    """Raised when upload fails."""
    pass


class StorageDownloadError(StorageError):
    """Raised when download fails."""
    pass


class Storage:
    """Local storage abstraction for media files."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or os.environ.get("STORAGE_PATH", "./storage"))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, key: str) -> Path:
        return self.base_path / key
    
    def upload(self, local_path: str, key: str) -> dict:
        """Upload a file to storage.
        
        Args:
            local_path: Source file path
            key: Destination key/path in storage
            
        Returns:
            Dictionary with metadata
        """
        source = Path(local_path)
        if not source.exists():
            raise StorageUploadError(f"Source file not found: {local_path}")
        
        dest = self._resolve_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        dest.write_bytes(source.read_bytes())
        
        return {
            "key": key,
            "size": dest.stat().st_size,
            "uploaded_at": datetime.utcnow().isoformat(),
        }
    
    def download(self, key: str, local_path: str) -> dict:
        """Download a file from storage.
        
        Args:
            key: Source key/path in storage
            local_path: Destination local path
            
        Returns:
            Dictionary with metadata
        """
        source = self._resolve_path(key)
        if not source.exists():
            raise StorageDownloadError(f"File not found in storage: {key}")
        
        dest = Path(local_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        dest.write_bytes(source.read_bytes())
        
        return {
            "key": key,
            "size": dest.stat().st_size,
            "downloaded_at": datetime.utcnow().isoformat(),
        }
    
    def exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        return self._resolve_path(key).exists()
    
    def delete(self, key: str) -> bool:
        """Delete a file from storage."""
        path = self._resolve_path(key)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def list(self, prefix: str = "") -> List[dict]:
        """List files in storage with optional prefix."""
        results = []
        search_path = self._resolve_path(prefix) if prefix else self.base_path
        
        if search_path.is_file():
            return [{"key": prefix, "size": search_path.stat().st_size}]
        
        for path in search_path.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(self.base_path)
                results.append({
                    "key": str(rel_path),
                    "size": path.stat().st_size,
                })
        
        return results
