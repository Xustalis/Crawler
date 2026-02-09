"""
Data models for aggregated scraping results.

Provides structured data classes for resource aggregation,
eliminating the need to display individual URLs to users.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

from .models import Resource


class ResourceCategory(Enum):
    """Categories of web resources that can be scraped."""
    IMAGES = auto()
    VIDEOS = auto()
    AUDIOS = auto()
    DOCUMENTS = auto()
    M3U8_STREAMS = auto()


@dataclass
class ScrapedData:
    """
    Aggregated scraping results by resource category.
    
    Attributes:
        images: List of discovered image Resources
        videos: List of discovered video Resources
        audios: List of discovered audio Resources
        documents: List of discovered document Resources (includes JSON/Text)
        m3u8_streams: List of discovered M3U8 Resources
        source_url: The original URL that was scraped
    """
    
    images: List[Resource] = field(default_factory=list)
    videos: List[Resource] = field(default_factory=list)
    audios: List[Resource] = field(default_factory=list)
    documents: List[Resource] = field(default_factory=list)
    m3u8_streams: List[Resource] = field(default_factory=list)
    source_url: str = ""
    
    def is_empty(self) -> bool:
        """Check if no resources were found."""
        return (
            len(self.images) == 0 and
            len(self.videos) == 0 and
            len(self.audios) == 0 and
            len(self.documents) == 0 and
            len(self.m3u8_streams) == 0
        )
    
    def total_count(self) -> int:
        """Get total number of discovered resources."""
        return (
            len(self.images) +
            len(self.videos) +
            len(self.audios) +
            len(self.documents) +
            len(self.m3u8_streams)
        )
    
    def get_category_counts(self) -> Dict[ResourceCategory, int]:
        """
        Get resource counts by category.
        
        Returns:
            Dict mapping category to count
        """
        return {
            ResourceCategory.IMAGES: len(self.images),
            ResourceCategory.VIDEOS: len(self.videos),
            ResourceCategory.AUDIOS: len(self.audios),
            ResourceCategory.DOCUMENTS: len(self.documents),
            ResourceCategory.M3U8_STREAMS: len(self.m3u8_streams),
        }
    
    def get_resources_by_category(self, category: ResourceCategory) -> List[Resource]:
        """
        Get Resource list for a specific category.
        
        Args:
            category: The resource category
        
        Returns:
            List of Resource objects
        """
        mapping = {
            ResourceCategory.IMAGES: self.images,
            ResourceCategory.VIDEOS: self.videos,
            ResourceCategory.AUDIOS: self.audios,
            ResourceCategory.DOCUMENTS: self.documents,
            ResourceCategory.M3U8_STREAMS: self.m3u8_streams,
        }
        return mapping.get(category, [])
        
    def get_urls_by_category(self, category: ResourceCategory) -> List[str]:
        """
        Get URL list for a specific category (Backward Compatibility).
        """
        resources = self.get_resources_by_category(category)
        return [r.url for r in resources if r.url]
    
    def summary(self) -> str:
        """
        Generate human-readable summary.
        
        Returns:
            Summary string like "Found: 128 images, 3 videos, 0 audio"
        """
        parts = []
        
        if self.images:
            parts.append(f"{len(self.images)} 张图片")
        if self.videos:
            parts.append(f"{len(self.videos)} 个视频")
        if self.audios:
            parts.append(f"{len(self.audios)} 个音频")
        if self.documents:
            parts.append(f"{len(self.documents)} 个文档")
        if self.m3u8_streams:
            parts.append(f"{len(self.m3u8_streams)} 个 M3U8 流")
        
        if not parts:
            return "未发现任何资源"
        
        return f"发现: {', '.join(parts)}"
    
    def summary_en(self) -> str:
        """Generate English summary."""
        parts = []
        
        if self.images:
            parts.append(f"{len(self.images)} images")
        if self.videos:
            parts.append(f"{len(self.videos)} videos")
        if self.audios:
            parts.append(f"{len(self.audios)} audios")
        if self.documents:
            parts.append(f"{len(self.documents)} documents")
        if self.m3u8_streams:
            parts.append(f"{len(self.m3u8_streams)} M3U8 streams")
        
        if not parts:
            return "No resources found"
        
        return f"Found: {', '.join(parts)}"


# 资源分类的显示信息
CATEGORY_DISPLAY = {
    ResourceCategory.IMAGES: {
        'icon': '🖼️',
        'label_en': 'Images',
        'label_zh': '图片',
        'extensions': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico'},
        'default_selected': True,
    },
    ResourceCategory.VIDEOS: {
        'icon': '🎬',
        'label_en': 'Videos',
        'label_zh': '视频',
        'extensions': {'.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv'},
        'default_selected': True,
    },
    ResourceCategory.AUDIOS: {
        'icon': '🎵',
        'label_en': 'Audio',
        'label_zh': '音频',
        'extensions': {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'},
        'default_selected': False,
    },
    ResourceCategory.DOCUMENTS: {
        'icon': '📄',
        'label_en': 'Documents',
        'label_zh': '文档',
        'extensions': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'},
        'default_selected': False,
    },
    ResourceCategory.M3U8_STREAMS: {
        'icon': '📺',
        'label_en': 'M3U8 Streams',
        'label_zh': 'M3U8 流',
        'extensions': {'.m3u8', '.m3u'},
        'default_selected': True,
    },
}
