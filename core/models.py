"""
Data models for the Crawler application.

This module defines the core domain entities using dataclasses,
ensuring type safety and clean data representation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class ResourceType(Enum):
    """Enumeration of resource types."""
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    M3U8 = "m3u8"
    AUDIO = "audio"
    UNKNOWN = "unknown"
    JSON_DATA = "json_data"      # API/JSON responses
    RICH_TEXT = "rich_text"      # Markdown/HTML fragments


class DownloadStatus(Enum):
    """Enumeration of download states."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Resource:
    """
    Core data model representing a crawlable resource.
    
    Attributes:
        url: The resource URL
        resource_type: Type of the resource (video, image, etc.)
        title: Display name or description
        file_extension: Expected file extension (e.g., .mp4, .jpg)
        file_size: Size in bytes (None if unknown)
        headers: Custom HTTP headers required for download
        referer: Referer header for anti-hotlinking
        status: Current download status
        progress: Download progress (0.0 to 1.0)
        error_message: Error details if download failed
        created_at: Timestamp when resource was discovered
        local_path: Saved file path after successful download
    """
    
    url: str
    resource_type: ResourceType = ResourceType.UNKNOWN
    title: str = ""
    file_extension: str = ""
    file_size: Optional[int] = None
    headers: dict[str, str] = field(default_factory=dict)
    referer: Optional[str] = None
    
    # Download state tracking
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    local_path: Optional[str] = None
    
    content: str = ""                                    # Raw text/JSON content
    metadata: dict = field(default_factory=dict)         # Author, date, tags, etc.
    
    def __post_init__(self) -> None:
        """Validate and auto-infer missing fields."""
        # Auto-detect resource type from URL if not set
        if self.resource_type == ResourceType.UNKNOWN:
            self.resource_type = self._infer_type()
        
        # Auto-extract file extension
        if not self.file_extension and self.url:
            self.file_extension = self._extract_extension()
        
        # Generate default title if missing
        if not self.title:
            self.title = self._generate_title()
    
    def _infer_type(self) -> ResourceType:
        """Infer resource type from URL patterns."""
        url_lower = self.url.lower()
        
        if '.m3u8' in url_lower or 'm3u8' in url_lower:
            return ResourceType.M3U8
        elif any(ext in url_lower for ext in ['.mp4', '.avi', '.mkv', '.webm', '.flv']):
            return ResourceType.VIDEO
        elif any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
            return ResourceType.IMAGE
        elif any(ext in url_lower for ext in ['.mp3', '.wav', '.flac', '.aac']):
            return ResourceType.AUDIO
        else:
            return ResourceType.UNKNOWN
    
    def _extract_extension(self) -> str:
        """Extract file extension from URL."""
        # Remove query parameters
        clean_url = self.url.split('?')[0]
        
        if '.' in clean_url:
            ext = clean_url.rsplit('.', 1)[-1].lower()
            # Validate extension (max 5 chars)
            if len(ext) <= 5 and ext.isalnum():
                return f".{ext}"
        
        # Fallback based on resource type
        type_map = {
            ResourceType.VIDEO: ".mp4",
            ResourceType.M3U8: ".mp4",  # M3U8 merges to MP4
            ResourceType.IMAGE: ".jpg",
            ResourceType.AUDIO: ".mp3",
            ResourceType.TEXT: ".txt",
        }
        return type_map.get(self.resource_type, "")
    
    def _generate_title(self) -> str:
        """Generate a fallback title from URL."""
        # Extract filename from URL
        path = self.url.split('?')[0].split('/')[-1]
        if path and len(path) < 100:
            return path
        return f"{self.resource_type.value}_{self.created_at.strftime('%Y%m%d_%H%M%S')}"
    
    def mark_progress(self, progress: float) -> None:
        """
        Update download progress.
        
        Args:
            progress: Float between 0.0 and 1.0
        """
        self.progress = max(0.0, min(1.0, progress))
        if self.status == DownloadStatus.PENDING:
            self.status = DownloadStatus.DOWNLOADING
    
    def mark_completed(self, local_path: str) -> None:
        """Mark resource as successfully downloaded."""
        self.status = DownloadStatus.COMPLETED
        self.progress = 1.0
        self.local_path = local_path
        self.error_message = None
    
    def mark_failed(self, error: str) -> None:
        """Mark resource as failed with error message."""
        self.status = DownloadStatus.FAILED
        self.error_message = error
    
    def is_downloadable(self) -> bool:
        """Check if resource can be downloaded."""
        return self.status in [
            DownloadStatus.PENDING,
            DownloadStatus.PAUSED,
            DownloadStatus.FAILED
        ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'url': self.url,
            'type': self.resource_type.value,
            'title': self.title,
            'extension': self.file_extension,
            'size': self.file_size,
            'status': self.status.value,
            'progress': self.progress,
            'error': self.error_message,
            'local_path': self.local_path,
            'content': self.content,
            'metadata': self.metadata,
        }
