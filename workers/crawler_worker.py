"""
CrawlerWorker - QThread worker for crawling and downloading operations.

Implements the worker thread pattern with proper signal-based communication
and support for pause/cancel operations.
"""

from typing import List

from PyQt6.QtCore import QThread

from core.models import Resource, ResourceType, DownloadStatus
from core.parser import PageParser
from core.downloader import Downloader
from core.m3u8_handler import M3U8Handler
from utils.logger import setup_logger

from .signals import CrawlerSignals


logger = setup_logger(__name__)


class CrawlerWorker(QThread):
    """
    Worker thread for web crawling and downloading.
    
    Responsibilities:
    - Parse URL and extract resources
    - Download selected resources
    - Handle M3U8 streams
    - Report progress via signals
    - Support pause/cancel operations
    
    CRITICAL: Never call UI methods directly from this thread!
    All communication must go through signals.
    """
    
    def __init__(
        self,
        url: str,
        resources_to_download: List[Resource] = None,
        output_dir: str = './downloads'
    ):
        """
        Initialize worker thread.
        
        Args:
            url: URL to crawl (for analysis phase)
            resources_to_download: List of resources to download (for download phase)
            output_dir: Output directory for downloads
        """
        super().__init__()
        
        self.url = url
        self.resources_to_download = resources_to_download or []
        self.output_dir = output_dir
        
        # Signals
        self.signals = CrawlerSignals()
        
        # State flags
        self._is_cancelled = False
        self._is_paused = False
        
        # Components
        self.parser = PageParser()
        self.downloader = Downloader(output_dir=output_dir)
        self.m3u8_handler = M3U8Handler(output_dir=output_dir)
    
    def run(self) -> None:
        """
        Main worker thread execution.
        
        Override of QThread.run(). This method runs in the worker thread.
        """
        try:
            # Phase 1: Analysis (if URL provided)
            if self.url and not self.resources_to_download:
                self._run_analysis()
            
            # Phase 2: Download (if resources provided)
            if self.resources_to_download and not self._is_cancelled:
                self._run_downloads()
            
            # Emit completion signal
            if not self._is_cancelled:
                self.signals.task_finished.emit()
                self.signals.log_message.emit("✓ All tasks completed successfully")
            
        except Exception as e:
            error_msg = f"Worker error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.signals.error_occurred.emit(error_msg)
    
    def _run_analysis(self) -> None:
        """Execute URL analysis phase."""
        self.signals.analysis_started.emit()
        self.signals.log_message.emit(f"Analyzing URL: {self.url}")
        
        try:
            # Parse URL
            resources = self.parser.parse(self.url)
            
            if self._is_cancelled:
                return
            
            # Emit results
            self.signals.resources_found.emit(resources)
            self.signals.log_message.emit(f"Found {len(resources)} resources")
            self.signals.analysis_completed.emit()
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg)
            self.signals.error_occurred.emit(error_msg)
    
    def _run_downloads(self) -> None:
        """Execute download phase for all selected resources."""
        total = len(self.resources_to_download)
        completed = 0
        
        self.signals.log_message.emit(f"Starting download of {total} resource(s)...")
        
        for resource in self.resources_to_download:
            if self._is_cancelled:
                self.signals.log_message.emit("Download cancelled by user")
                break
            
            # Wait if paused
            while self._is_paused and not self._is_cancelled:
                self.msleep(100)
            
            # Download based on type
            success = self._download_resource(resource)
            
            if success:
                completed += 1
                self.signals.overall_progress.emit(completed, total)
        
        self.signals.log_message.emit(f"Downloads completed: {completed}/{total}")
    
    def _download_resource(self, resource: Resource) -> bool:
        """
        Download a single resource.
        
        Args:
            resource: Resource to download
        
        Returns:
            True if successful
        """
        self.signals.download_started.emit(resource)
        self.signals.log_message.emit(f"Downloading: {resource.title}")
        
        try:
            # Handle M3U8 streams
            if resource.resource_type == ResourceType.M3U8:
                success = self._download_m3u8(resource)
            else:
                success = self._download_regular(resource)
            
            if success:
                self.signals.download_completed.emit(resource)
                self.signals.log_message.emit(f"✓ Completed: {resource.title}")
            else:
                self.signals.download_failed.emit(resource, resource.error_message or "Unknown error")
                self.signals.log_message.emit(f"✗ Failed: {resource.title}")
            
            return success
            
        except Exception as e:
            error_msg = str(e)
            resource.mark_failed(error_msg)
            self.signals.download_failed.emit(resource, error_msg)
            self.signals.log_message.emit(f"✗ Error: {resource.title} - {error_msg}")
            return False
    
    def _download_regular(self, resource: Resource) -> bool:
        """Download regular file (non-M3U8)."""
        return self.downloader.download(
            resource,
            progress_callback=lambda p: self.signals.download_progress.emit(resource, p),
            is_cancelled=lambda: self._is_cancelled
        )
    
    def _download_m3u8(self, resource: Resource) -> bool:
        """Download and merge M3U8 stream."""
        self.signals.merging_started.emit(resource)
        
        success = self.m3u8_handler.download_m3u8(
            resource,
            progress_callback=lambda p: self.signals.download_progress.emit(resource, p),
            is_cancelled=lambda: self._is_cancelled
        )
        
        if success:
            self.signals.merging_completed.emit(resource)
        
        return success
    
    # Control methods (called from UI thread)
    
    def cancel(self) -> None:
        """Request cancellation of current operation."""
        self._is_cancelled = True
        self.signals.log_message.emit("Cancelling operation...")
        logger.info("Worker cancellation requested")
    
    def pause(self) -> None:
        """Pause download operations."""
        self._is_paused = True
        self.signals.log_message.emit("Downloads paused")
        logger.info("Worker paused")
    
    def resume(self) -> None:
        """Resume download operations."""
        self._is_paused = False
        self.signals.log_message.emit("Downloads resumed")
        logger.info("Worker resumed")
    
    def is_running_task(self) -> bool:
        """Check if worker is currently running."""
        return self.isRunning()
