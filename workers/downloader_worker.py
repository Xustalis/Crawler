"""
Downloader Worker for batch downloading by category.

Handles downloading resources after user selects categories
from the aggregated results panel.
"""

from typing import List, Optional, Callable, Set
from pathlib import Path
import os

from PyQt6.QtCore import QThread, pyqtSignal, QObject
import requests

from core.scraped_data import ScrapedData, ResourceCategory
from utils.sanitizer import sanitize_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DownloaderSignals(QObject):
    """Signals for the downloader worker."""
    
    # 下载开始
    started = pyqtSignal()
    
    # 单个文件进度 (url, progress 0-1)
    file_progress = pyqtSignal(str, float)
    
    # 单个文件完成
    file_completed = pyqtSignal(str)
    
    # 单个文件失败
    file_failed = pyqtSignal(str, str)
    
    # 整体进度 (completed, total)
    overall_progress = pyqtSignal(int, int)
    
    # 全部完成
    finished = pyqtSignal(int, int)  # (success_count, total_count)
    
    # 日志
    log = pyqtSignal(str)


class DownloaderWorker(QThread):
    """
    Batch Downloader Worker Thread.
    
    Downloads resources based on user-selected categories.
    Users don't need to confirm individual files.
    """
    
    CHUNK_SIZE = 8192
    
    def __init__(
        self,
        scraped_data: ScrapedData,
        selected_categories: List[ResourceCategory],
        output_dir: str,
        parent=None
    ):
        super().__init__(parent)
        self.scraped_data = scraped_data
        self.selected_categories = selected_categories
        self.output_dir = output_dir
        self.signals = DownloaderSignals()
        
        self._is_cancelled = False
        self._is_paused = False
    
    def run(self) -> None:
        """Execute the batch download task."""
        try:
            self.signals.started.emit()
            
            # 收集所有待下载的 URL
            urls_to_download: List[str] = []
            for category in self.selected_categories:
                urls_to_download.extend(
                    self.scraped_data.get_urls_by_category(category)
                )
            
            total = len(urls_to_download)
            if total == 0:
                self.signals.log.emit("⚠️ 没有可下载的资源")
                self.signals.finished.emit(0, 0)
                return
            
            self.signals.log.emit(f"📥 开始下载 {total} 个文件...")
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 下载每个文件
            success_count = 0
            for i, url in enumerate(urls_to_download):
                if self._is_cancelled:
                    break
                
                # 暂停检查
                while self._is_paused and not self._is_cancelled:
                    self.msleep(100)
                
                # 下载单个文件
                if self._download_file(url):
                    success_count += 1
                    self.signals.file_completed.emit(url)
                
                # 更新整体进度
                self.signals.overall_progress.emit(i + 1, total)
            
            # 完成
            if self._is_cancelled:
                self.signals.log.emit("⏹️ 下载已取消")
            else:
                self.signals.log.emit(f"✓ 下载完成: {success_count}/{total} 成功")
            
            self.signals.finished.emit(success_count, total)
            
        except Exception as e:
            logger.exception("Downloader worker error")
            self.signals.log.emit(f"❌ 下载出错: {str(e)}")
    
    def _download_file(self, url: str) -> bool:
        """
        Download a single file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # 获取文件名
            filename = self._extract_filename(url)
            filepath = Path(self.output_dir) / filename
            
            # 避免覆盖同名文件
            filepath = self._get_unique_path(filepath)
            
            # 发起请求
            headers = {
                'User-Agent': (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                ),
                'Referer': self.scraped_data.source_url,
            }
            
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # 写入文件
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if self._is_cancelled:
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 报告进度
                        if total_size > 0:
                            progress = downloaded / total_size
                            self.signals.file_progress.emit(url, progress)
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to download {url}: {e}")
            self.signals.file_failed.emit(url, str(e))
            return False
    
    def _extract_filename(self, url: str) -> str:
        """Extract and sanitize filename from URL."""
        from urllib.parse import urlparse, unquote
        
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            filename = os.path.basename(path)
            
            if not filename or filename == '/':
                # 使用 URL hash 作为文件名
                import hashlib
                hash_name = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"file_{hash_name}"
            
            return sanitize_filename(filename)
            
        except Exception:
            import hashlib
            hash_name = hashlib.md5(url.encode()).hexdigest()[:8]
            return f"file_{hash_name}"
    
    def _get_unique_path(self, filepath: Path) -> Path:
        """Get unique filepath to avoid overwriting."""
        if not filepath.exists():
            return filepath
        
        stem = filepath.stem
        suffix = filepath.suffix
        parent = filepath.parent
        counter = 1
        
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    def cancel(self) -> None:
        """Cancel the download."""
        self._is_cancelled = True
    
    def pause(self) -> None:
        """Pause the download."""
        self._is_paused = True
    
    def resume(self) -> None:
        """Resume the download."""
        self._is_paused = False
