"""Local filesystem storage with S3-compatible interface.

Fallback for development/testing when MinIO is not available.
Stores files in local directory with same API as boto3 S3.
"""

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional
from datetime import datetime
import mimetypes

from .storage_provider import StorageProvider, FileMetadata


class LocalS3Storage(StorageProvider):
    """S3-compatible storage using local filesystem.
    
    Suitable for development/POC. In production, use real S3 or MinIO.
    """
    
    def __init__(self, base_path: str = "/tmp/project_atlas_storage"):
        """Initialize local storage.
        
        Args:
            base_path: Root directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get absolute file path for a key."""
        # Ensure key doesn't escape base_path
        safe_key = key.lstrip("/")
        file_path = self.base_path / safe_key
        
        # Security check
        if not str(file_path.resolve()).startswith(str(self.base_path.resolve())):
            raise ValueError(f"Invalid key: {key}")
        
        return file_path
    
    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        content_type: Optional[str] = None
    ) -> FileMetadata:
        """Upload file from file-like object."""
        file_path = self._get_file_path(key)
        
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(fileobj, f)
        
        # Get file stats
        stat = file_path.stat()
        
        # Guess content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(file_path))
        
        return FileMetadata(
            key=key,
            size=stat.st_size,
            content_type=content_type,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime),
            url=f"file://{file_path}"  # Local file URL
        )
    
    def download_fileobj(self, key: str, fileobj: BinaryIO) -> None:
        """Download file to file-like object."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        
        with open(file_path, 'rb') as f:
            shutil.copyfileobj(f, fileobj)
    
    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """Get 'presigned' URL (just file path for local storage).
        
        In local storage, we just return the file path.
        In real S3, this would be a time-limited signed URL.
        """
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        
        # Return file:// URL (in real app, return HTTP presigned URL)
        return f"file://{file_path}"
    
    def delete(self, key: str) -> None:
        """Delete file."""
        file_path = self._get_file_path(key)
        
        if file_path.exists():
            file_path.unlink()
    
    def exists(self, key: str) -> bool:
        """Check if file exists."""
        file_path = self._get_file_path(key)
        return file_path.exists()