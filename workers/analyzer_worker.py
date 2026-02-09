"""
Refactored Crawler Worker with smart URL handling and aggregated results.

Focuses on user experience:
- Smart URL normalization with HTTPS/HTTP fallback
- Aggregated results by category (no raw URL lists shown to users)
- Clean signal-based communication
"""

from typing import Optional, Set
from urllib.parse import urljoin, urlparse
import re

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from core.scraped_data import ScrapedData, ResourceCategory, CATEGORY_DISPLAY
from utils.url_normalizer import normalize_url, fetch_with_fallback
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AnalyzerSignals(QObject):
    """Signals for the analyzer worker."""
    
    # 分析开始
    started = pyqtSignal()
    
    # 分析进度 (阶段描述)
    progress = pyqtSignal(str)
    
    # 分析完成，返回聚合结果
    finished = pyqtSignal(ScrapedData)
    
    # 发生错误
    error = pyqtSignal(str)
    
    # 日志消息
    log = pyqtSignal(str)


class AnalyzerWorker(QThread):
    """
    Analyzer Worker Thread.
    
    Responsibilities:
    1. Fetch webpage content (with HTTPS->HTTP fallback)
    2. Parse HTML and extract resources
    3. Categorize resources into ScrapedData
    4. Emit aggregated results to UI
    
    This worker ONLY does analysis. Download is handled separately.
    """
    
    # 资源文件扩展名映射
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico', '.avif'}
    VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'}
    DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
    
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.signals = AnalyzerSignals()
        self._is_cancelled = False
    
    def run(self) -> None:
        """Execute the analysis task."""
        try:
            self.signals.started.emit()
            self.signals.progress.emit("正在初始化解析器...")
            
            # Use core.parser.PageParser for universal parsing
            from core.parser import PageParser
            from core.models import ResourceType
            
            parser = PageParser()
            
            # Step 1: Parse URL
            self.signals.progress.emit("正在分析网页内容...")
            self.signals.log.emit(f"📡 正在分析: {self.url}")
            
            # parse returns (resources, links)
            resources, _ = parser.parse(self.url)
            
            if self._is_cancelled:
                return
            
            # Step 2: Categorize Results
            self.signals.progress.emit("正在分类资源...")
            scraped_data = ScrapedData()
            scraped_data.source_url = self.url
            
            for res in resources:
                if res.resource_type == ResourceType.IMAGE:
                    scraped_data.images.append(res)
                elif res.resource_type == ResourceType.VIDEO:
                    scraped_data.videos.append(res)
                elif res.resource_type == ResourceType.AUDIO:
                    scraped_data.audios.append(res)
                elif res.resource_type == ResourceType.M3U8:
                    scraped_data.m3u8_streams.append(res)
                elif res.resource_type in (ResourceType.TEXT, ResourceType.JSON_DATA, ResourceType.RICH_TEXT):
                    scraped_data.documents.append(res)
                else:
                    # Try to fallback based on extension for unknown types
                    if res.file_extension in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}:
                        scraped_data.documents.append(res)
            
            if self._is_cancelled:
                return
            
            # Step 3: Emit Results
            self.signals.log.emit(f"✓ 分析完成: {scraped_data.summary()}")
            self.signals.finished.emit(scraped_data)
            
        except Exception as e:
            logger.exception("Analyzer worker error")
            self.signals.error.emit(f"分析失败: {str(e)}")

    def cancel(self) -> None:
        """Cancel the analysis."""
        self._is_cancelled = True
