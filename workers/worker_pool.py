"""
Worker pool manager for concurrent crawling.

Manages multiple RequestWorker threads and aggregates their results.
"""

from typing import List, Optional
from collections import defaultdict

from PyQt6.QtCore import QObject, pyqtSignal

from core.crawl_queue import CrawlQueue, CrawlTask, Priority
from core.scraped_data import ScrapedData
from core.models import Resource, ResourceType
from workers.request_worker import RequestWorker
from utils.logger import setup_logger


logger = setup_logger(__name__)


class WorkerPool(QObject):
    """
    Manages a pool of concurrent RequestWorker threads.
    
    Coordinates task distribution, result aggregation, and progress reporting.
    """
    
    # Signals
    pool_started = pyqtSignal()
    pool_progress = pyqtSignal(int, int)  # completed, total
    pool_finished = pyqtSignal(object)  # ScrapedData
    log_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, num_workers: int = 5, max_depth: int = 2):
        """
        Initialize worker pool.
        
        Args:
            num_workers: Number of concurrent workers (1-20)
            max_depth: Maximum crawl depth
        """
        super().__init__()
        
        self.num_workers = min(max(1, num_workers), 20)  # Clamp to 1-20
        self.max_depth = max_depth
        
        # Queue and workers
        self.crawl_queue = CrawlQueue()
        self.workers: List[RequestWorker] = []
        
        # Results aggregation
        self.scraped_data: Optional[ScrapedData] = None
        self._results_lock = None  # Will use threading.Lock if needed
    
    def start_crawl(self, seed_url: str):
        """
        Start crawling from seed URL.
        
        Args:
            seed_url: Starting URL
        """
        # Initialize ScrapedData
        self.scraped_data = ScrapedData(source_url=seed_url)
        
        # Add seed task
        seed_task = CrawlTask(url=seed_url, depth=1, priority=Priority.HIGH)
        self.crawl_queue.put(seed_task)
        
        # Create and start workers
        for i in range(self.num_workers):
            worker = RequestWorker(worker_id=i, crawl_queue=self.crawl_queue)
            
            # Connect signals
            worker.task_started.connect(self._on_task_started)
            worker.task_completed.connect(self._on_task_completed)
            worker.task_failed.connect(self._on_task_failed)
            worker.log_message.connect(self.log_message.emit)
            worker.finished.connect(lambda: self._on_worker_finished())
            
            self.workers.append(worker)
            worker.start()
        
        self.pool_started.emit()
        self.log_message.emit(f"Started {self.num_workers} workers for {seed_url}")
    
    def _on_task_started(self, url: str):
        """Handle task start."""
        stats = self.crawl_queue.get_stats()
        self.pool_progress.emit(stats['completed'], stats['total_queued'])
    
    def _on_task_completed(self, url: str, resources: List[Resource], links: List[str]):
        """
        Handle task completion - aggregate results and queue new links.
        
        Args:
            url: Completed URL
            resources: Extracted resources
            links: Discovered links
        """
        # Categorize resources
        for res in resources:
            if res.resource_type == ResourceType.IMAGE:
                self.scraped_data.images.append(res)
            elif res.resource_type == ResourceType.VIDEO:
                self.scraped_data.videos.append(res)
            elif res.resource_type == ResourceType.AUDIO:
                self.scraped_data.audios.append(res)
            elif res.resource_type == ResourceType.M3U8:
                self.scraped_data.m3u8_streams.append(res)
            elif res.resource_type in (ResourceType.TEXT, ResourceType.JSON_DATA, ResourceType.RICH_TEXT):
                self.scraped_data.documents.append(res)
            else:
                # Fallback
                if res.file_extension in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}:
                    self.scraped_data.documents.append(res)
        
        # Queue pagination links (if within depth limit)
        # For now, we'll use a simple heuristic: the task that produced these links had some depth
        # We need to track depth per URL - simplified: assume depth 1, next is 2
        # In full implementation, we'd pass original task's depth
        # For this MVP, we'll just queue up to max_depth=2
        for link in links:
            # Simplified: queue all links as depth 2
            next_task = CrawlTask(url=link, depth=2, priority=Priority.NORMAL, referer=url)
            if self.max_depth >= 2:
                self.crawl_queue.put(next_task)
        
        # Update progress
        stats = self.crawl_queue.get_stats()
        self.pool_progress.emit(stats['completed'], stats['total_queued'])
        
        self.log_message.emit(f"Completed {url}: {len(resources)} resources, {len(links)} links")
    
    def _on_task_failed(self, url: str, error: str):
        """Handle task failure."""
        self.log_message.emit(f"Failed {url}: {error}")
        
        # Update progress
        stats = self.crawl_queue.get_stats()
        self.pool_progress.emit(stats['completed'], stats['total_queued'])
    
    def _on_worker_finished(self):
        """Check if all workers are done."""
        # Check if all workers have finished
        all_done = all(worker.isFinished() for worker in self.workers)
        
        if all_done:
            stats = self.crawl_queue.get_stats()
            
            # CRITICAL DEBUG: Log what we're about to emit
            img_count = len(self.scraped_data.images)
            vid_count = len(self.scraped_data.videos)
            m3u8_count = len(self.scraped_data.m3u8_streams)
            doc_count = len(self.scraped_data.documents)
            aud_count = len(self.scraped_data.audios)
            
            self.log_message.emit(
                f"DEBUG: Emitting ScrapedData - "
                f"Images:{img_count}, Videos:{vid_count}, M3U8:{m3u8_count}, "
                f"Docs:{doc_count}, Audio:{aud_count}"
            )
            self.log_message.emit(f"All workers finished. Stats: {stats}")
            
            # Ensure we're emitting valid data
            if self.scraped_data is None:
                self.log_message.emit("ERROR: scraped_data is None!")
                self.scraped_data = ScrapedData(source_url="unknown")
            
            self.pool_finished.emit(self.scraped_data)
    
    def cancel(self):
        """Cancel all workers."""
        self.log_message.emit("Cancelling worker pool...")
        
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish (with timeout)
        for worker in self.workers:
            worker.wait(2000)  # 2 second timeout
