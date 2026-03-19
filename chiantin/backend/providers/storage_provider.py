"""Storage provider interface (S3-compatible)."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileMetadata:
    """File metadata returned by storage operations."""
    key: str
    size: int
    content_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    url: Optional[str] = None  # Public or presigned URL


class StorageProvider(ABC):
    """Abstract storage provider interface (S3-compatible API).
    
    All implementations (LocalS3, real S3, MinIO) must implement this.
    """
    
    @abstractmethod
    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        content_type: Optional[str] = None
    ) -> FileMetadata:
        """Upload a file-like object.
        
        Args:
            fileobj: File-like object to upload
            key: Object key (path) in storage
            content_type: MIME type (optional)
        
        Returns:
            FileMetadata with upload details
        """
        pass
    
    @abstractmethod
    def download_fileobj(self, key: str, fileobj: BinaryIO) -> None:
        """Download file to a file-like object.
        
        Args:
            key: Object key in storage
            fileobj: File-like object to write to
        
        Raises:
            FileNotFoundError: If key doesn't exist
        """
        pass
    
    @abstractmethod
    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """Generate a presigned URL for temporary access.
        
        Args:
            key: Object key
            expires_in: Expiry in seconds (default 1 hour)
        
        Returns:
            Presigned URL string
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an object.
        
        Args:
            key: Object key to delete
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if object exists.
        
        Args:
            key: Object key
        
        Returns:
            True if exists, False otherwise
        """
        pass