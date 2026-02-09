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
            
            # Step 1: 规范化 URL
            self.signals.progress.emit("正在规范化 URL...")
            normalized_url = normalize_url(self.url)
            
            if not normalized_url:
                self.signals.error.emit("请输入有效的网址")
                return
            
            self.signals.log.emit(f"📡 正在分析: {normalized_url}")
            
            # Step 2: 获取网页内容 (带 HTTPS->HTTP 降级)
            self.signals.progress.emit("正在获取网页内容...")
            
            try:
                response, final_url = fetch_with_fallback(normalized_url)
            except RequestException as e:
                self.signals.error.emit(str(e))
                return
            
            if self._is_cancelled:
                return
            
            self.signals.log.emit(f"✓ 成功获取网页 ({len(response.content)} bytes)")
            
            # Step 3: 解析 HTML
            self.signals.progress.emit("正在解析网页内容...")
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Step 4: 提取并分类资源
            self.signals.progress.emit("正在分类资源...")
            scraped_data = self._extract_and_categorize(soup, final_url)
            scraped_data.source_url = final_url
            
            if self._is_cancelled:
                return
            
            # Step 5: 发送聚合结果
            self.signals.log.emit(f"✓ 分析完成: {scraped_data.summary()}")
            self.signals.finished.emit(scraped_data)
            
        except Exception as e:
            logger.exception("Analyzer worker error")
            self.signals.error.emit(f"分析失败: {str(e)}")
    
    def _extract_and_categorize(self, soup: BeautifulSoup, base_url: str) -> ScrapedData:
        """
        Extract resources from HTML and categorize them.
        
        遵循优先级：视频 > M3U8 > 图片 > 音频 > 文档
        去重处理，避免重复 URL
        """
        scraped = ScrapedData()
        seen_urls: Set[str] = set()
        
        # 1. 提取 <img> 标签中的图片
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                url = self._resolve_url(src, base_url)
                if url and url not in seen_urls:
                    if self._has_extension(url, self.IMAGE_EXTENSIONS):
                        scraped.images.append(url)
                        seen_urls.add(url)
        
        # 2. 提取 <video> 和 <source> 标签中的视频
        for video in soup.find_all(['video', 'source']):
            src = video.get('src')
            if src:
                url = self._resolve_url(src, base_url)
                if url and url not in seen_urls:
                    # 检查是否为 M3U8 流
                    if '.m3u8' in url.lower() or '.m3u' in url.lower():
                        scraped.m3u8_streams.append(url)
                    elif self._has_extension(url, self.VIDEO_EXTENSIONS):
                        scraped.videos.append(url)
                    seen_urls.add(url)
        
        # 3. 从 <script> 和文本中检测 M3U8 链接
        page_text = str(soup)
        m3u8_pattern = r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*'
        for match in re.findall(m3u8_pattern, page_text, re.IGNORECASE):
            url = match.rstrip('\\').rstrip('"').rstrip("'")
            if url not in seen_urls:
                scraped.m3u8_streams.append(url)
                seen_urls.add(url)
        
        # 4. 提取 <audio> 标签中的音频
        for audio in soup.find_all(['audio', 'source']):
            src = audio.get('src')
            if src:
                url = self._resolve_url(src, base_url)
                if url and url not in seen_urls:
                    if self._has_extension(url, self.AUDIO_EXTENSIONS):
                        scraped.audios.append(url)
                        seen_urls.add(url)
        
        # 5. 提取 <a> 链接中的资源
        for link in soup.find_all('a', href=True):
            href = link['href']
            url = self._resolve_url(href, base_url)
            if url and url not in seen_urls:
                # 分类链接类型
                if self._has_extension(url, self.IMAGE_EXTENSIONS):
                    scraped.images.append(url)
                elif self._has_extension(url, self.VIDEO_EXTENSIONS):
                    scraped.videos.append(url)
                elif self._has_extension(url, self.AUDIO_EXTENSIONS):
                    scraped.audios.append(url)
                elif self._has_extension(url, self.DOCUMENT_EXTENSIONS):
                    scraped.documents.append(url)
                elif '.m3u8' in url.lower():
                    scraped.m3u8_streams.append(url)
                else:
                    continue  # 跳过普通链接
                seen_urls.add(url)
        
        logger.info(
            f"Extracted: {len(scraped.images)} images, "
            f"{len(scraped.videos)} videos, "
            f"{len(scraped.m3u8_streams)} M3U8 streams"
        )
        
        return scraped
    
    def _resolve_url(self, url: str, base_url: str) -> Optional[str]:
        """Resolve relative URL to absolute."""
        if not url:
            return None
        
        url = url.strip()
        
        # 跳过 data URI 和 javascript
        if url.startswith(('data:', 'javascript:', '#', 'mailto:')):
            return None
        
        # 转换为绝对 URL
        try:
            resolved = urljoin(base_url, url)
            # 验证是有效的 HTTP(S) URL
            parsed = urlparse(resolved)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                return resolved
        except Exception:
            pass
        
        return None
    
    def _has_extension(self, url: str, extensions: Set[str]) -> bool:
        """Check if URL has one of the specified extensions."""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            return any(path.endswith(ext) for ext in extensions)
        except Exception:
            return False
    
    def cancel(self) -> None:
        """Cancel the analysis."""
        self._is_cancelled = True
