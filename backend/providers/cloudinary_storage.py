"""Cloudinary storage provider implementation."""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import BinaryIO, Optional
from datetime import datetime
from .storage_provider import StorageProvider, FileMetadata
from config import settings


class CloudinaryStorage(StorageProvider):
    """Cloudinary-based storage provider for permanent file storage."""
    
    def __init__(self):
        """Initialize Cloudinary with settings."""
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        self.cloud_name = settings.CLOUDINARY_CLOUD_NAME
    
    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        content_type: Optional[str] = None
    ) -> FileMetadata:
        """Upload a file to Cloudinary.
        
        Args:
            fileobj: File-like object to upload
            key: Object key (path) - will be used as public_id
            content_type: MIME type (optional)
        
        Returns:
            FileMetadata with upload details including Cloudinary URL
        """
        # Determine resource type based on content_type
        resource_type = "image"  # Default to image
        if content_type:
            if content_type.startswith("video/"):
                resource_type = "video"
            elif not content_type.startswith("image/"):
                resource_type = "raw"  # For PDFs, docs, etc.
        
        # Always remove extension from public_id
        # Cloudinary account has strict delivery that blocks raw files with extensions in URL
        public_id = key.rsplit('.', 1)[0] if '.' in key else key
        
        # Read file content
        file_content = fileobj.read()
        file_size = len(file_content)
        
        # Reset file pointer for upload
        fileobj.seek(0)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            fileobj,
            public_id=public_id,
            resource_type=resource_type,
            folder="",  # Public ID already contains the folder structure
            overwrite=True,
            invalidate=True
        )
        
        # Use the URL returned by Cloudinary directly
        # Do NOT append extension - this Cloudinary account blocks raw files with extensions in URL
        url = result.get("secure_url", result.get("url"))
        
        return FileMetadata(
            key=key,
            size=file_size,
            content_type=content_type,
            uploaded_at=datetime.utcnow(),
            url=url
        )
    
    def download_fileobj(self, key: str, fileobj: BinaryIO) -> None:
        """Download file from Cloudinary to a file-like object.
        
        Note: Cloudinary files are accessed via URL, so this method
        fetches the file using the URL.
        """
        import urllib.request
        
        url = self.get_presigned_url(key)
        with urllib.request.urlopen(url) as response:
            fileobj.write(response.read())
    
    def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """Get the public URL for a Cloudinary asset.
        
        Note: Cloudinary URLs are public by default. For private assets,
        you would use signed URLs, but for KYC documents we use public URLs
        with obscure paths for simplicity.
        """
        # Clean the key to get public_id
        public_id = key.rsplit('.', 1)[0] if '.' in key else key
        
        # Determine the format/extension
        ext = key.rsplit('.', 1)[1].lower() if '.' in key else 'jpg'
        
        # Determine resource type based on extension or content_type
        # PDFs, documents, and other non-image/video files use "raw"
        raw_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                         'txt', 'csv', 'zip', 'rar', '7z', 'tar', 'gz',
                         'json', 'xml', 'html', 'css', 'js'}
        video_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv', 'flv'}
        
        if ext in raw_extensions:
            resource_type = "raw"
        elif ext in video_extensions:
            resource_type = "video"
        else:
            resource_type = "image"
        
        # Build Cloudinary URL with correct resource type
        # For images: https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}.{ext}
        # For raw files: https://res.cloudinary.com/{cloud_name}/raw/upload/{public_id}.{ext}
        # For videos: https://res.cloudinary.com/{cloud_name}/video/upload/{public_id}.{ext}
        url = f"https://res.cloudinary.com/{self.cloud_name}/{resource_type}/upload/{public_id}.{ext}"
        
        return url
    
    def get_url(self, key: str) -> str:
        """Get the direct URL for a Cloudinary asset."""
        return self.get_presigned_url(key)
    
    def delete(self, key: str) -> None:
        """Delete a file from Cloudinary."""
        public_id = key.rsplit('.', 1)[0] if '.' in key else key
        cloudinary.uploader.destroy(public_id, invalidate=True)
    
    def exists(self, key: str) -> bool:
        """Check if file exists in Cloudinary."""
        try:
            public_id = key.rsplit('.', 1)[0] if '.' in key else key
            cloudinary.api.resource(public_id)
            return True
        except cloudinary.exceptions.NotFound:
            return False
        except Exception:
            return False
