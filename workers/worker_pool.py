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
from core.database import DatabaseManager
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
        self.threads: List[QThread] = [] # Keep track of threads
        
        # Results aggregation
        self.scraped_data: Optional[ScrapedData] = None
        self._results_lock = None  # Will use threading.Lock if needed
        
        # Database
        self.db = DatabaseManager()
        self.task_id = -1
    
    def start_crawl(self, seed_url: str, auto_concurrency: bool = False):
        """
        Start crawling from seed URL.
        
        Args:
            seed_url: Starting URL
            auto_concurrency: Enable adaptive concurrency
        """
        self.auto_concurrency = auto_concurrency
        
        # Initialize ScrapedData
        self.scraped_data = ScrapedData(source_url=seed_url)
        
        # Create Task in DB (Mark as 'scanning')
        self.task_id = self.db.create_task(seed_url, save_path="[SCAN ONLY]")
        self.db.update_task_status(self.task_id, "scanning")
        
        # Add seed task
        seed_task = CrawlTask(url=seed_url, depth=1, priority=Priority.HIGH)
        self.crawl_queue.put(seed_task)
        
        # Initialize thread tracking
        self.active_workers_count = 0
        self._pool_finished_emitted = False
        
        # Create and start workers
        self._spawn_workers(self.num_workers)
        
        # Start Auto-Concurrency Timer
        if self.auto_concurrency:
            from PyQt6.QtCore import QTimer
            self.adjust_timer = QTimer()
            self.adjust_timer.timeout.connect(self._adjust_concurrency)
            self.adjust_timer.start(2000) # Check every 2s

        self.pool_started.emit()
        self.log_message.emit(f"Started {self.num_workers} workers for {seed_url} (Auto: {auto_concurrency})")
    
    def _spawn_workers(self, count: int):
        from PyQt6.QtCore import QThread
        
        current_count = len(self.workers)
        target = current_count + count
        
        for i in range(current_count, target):
            if i >= 20: break # Hard limit
            
            thread = QThread()
            self.threads.append(thread)
            
            worker = RequestWorker(worker_id=i, crawl_queue=self.crawl_queue)
            self.workers.append(worker)
            
            worker.moveToThread(thread)
            
            thread.started.connect(worker.process_queue)
            
            worker.task_started.connect(self._on_task_started)
            worker.task_completed.connect(self._on_task_completed)
            worker.task_failed.connect(self._on_task_failed)
            worker.log_message.connect(self.log_message.emit)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            
            # Use a robust active counter
            # Note: We don't connect finished to on_worker_finished directly anymore
            # We rely on periodic check or counter
            
            thread.start()
            self.active_workers_count += 1
            
    def _adjust_concurrency(self):
        """Dynamically adjust worker count based on queue size."""
        # Simple heuristic:
        # If queue > 50 and workers < max, add workers
        # If queue < 5, maybe we are fine (we don't kill workers usually, just let them idle/finish)
        
        q_size = self.crawl_queue.size()
        
        if q_size > 50 and len(self.workers) < 20:
            new_workers = min(5, 20 - len(self.workers))
            if new_workers > 0:
                self.log_message.emit(f"Scale UP: Adding {new_workers} workers (Queue: {q_size})")
                self._spawn_workers(new_workers)
                
    def _on_task_started(self, url: str):
        """Handle task start."""
        stats = self.crawl_queue.get_stats()
        self.pool_progress.emit(stats['completed'], stats['total_queued'])
    
    def _on_task_completed(self, url: str, resources: List[Resource], links: List[str], depth: int):
        """
        Handle task completion - aggregate results and queue new links.
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
                if res.file_extension in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}:
                    self.scraped_data.documents.append(res)
        
        # Queue pagination links
        for link in links:
            if depth < self.max_depth:
                next_depth = depth + 1
                next_task = CrawlTask(url=link, depth=next_depth, priority=Priority.NORMAL, referer=url)
                self.crawl_queue.put(next_task)
        
        # Update progress
        stats = self.crawl_queue.get_stats()
        self.pool_progress.emit(stats['completed'], stats['total_queued'])
        self.log_message.emit(f"Completed {url}: {len(resources)} resources")
        
        self._check_finish_condition()

    def _on_task_failed(self, url: str, error: str):
        self.log_message.emit(f"Failed {url}: {error}")
        stats = self.crawl_queue.get_stats()
        self.pool_progress.emit(stats['completed'], stats['total_queued'])
        self._check_finish_condition()

    def _check_finish_condition(self):
        """Check if all tasks are done and queue is empty."""
        # This is called after every task done/fail
        if self.crawl_queue.is_empty() and self.crawl_queue.get_stats()['pending'] == 0:
             # Wait a brief moment or check if workers are idle?
             # Actually, if pending is 0 and queue is empty, and we just finished a task...
             # We might be done. But other workers might be in middle of task?
             # Better: Check self.crawl_queue.size() == 0.
             # AND we need to know if any worker is currently BUSY.
             # The queue being empty isn't enough if a worker is parsing.
             # We can't easily query worker state without complexity.
             # BUT: The queue is "task_done" only when processing finishes.
             # So queue.join() would block.
             
             # If we use queue.unfinished_tasks
             unfinished = self.crawl_queue._queue.unfinished_tasks
             if unfinished == 0:
                 self._finalize_pool()

    def _finalize_pool(self):
        if self._pool_finished_emitted:
            return
            
        self._pool_finished_emitted = True
        
        if hasattr(self, 'adjust_timer'):
            self.adjust_timer.stop()
            
        self.log_message.emit("All tasks completed.")
        
        # Stats
        stats = self.crawl_queue.get_stats()
        img_count = len(self.scraped_data.images)
        vid_count = len(self.scraped_data.videos)
        
        self.log_message.emit(
            f"DEBUG: ScrapedData - Images:{img_count}, Videos:{vid_count}"
        )
        
        # Ensure scraped_data
        if self.scraped_data is None:
             self.scraped_data = ScrapedData(source_url="unknown")

        # DB Update
        total_items = (len(self.scraped_data.images) + len(self.scraped_data.videos) + 
                      len(self.scraped_data.m3u8_streams) + len(self.scraped_data.documents) + 
                      len(self.scraped_data.audios))
                      
        self.db.update_task_progress(self.task_id, 0, total_items)
        self.db.update_task_status(self.task_id, "scanned", finished=True)
        
        self.pool_finished.emit(self.scraped_data)
        
        # Shutdown
        self.cancel()

    def cancel(self):
        """Cancel all workers."""
        if hasattr(self, 'adjust_timer'):
            self.adjust_timer.stop()

        self.log_message.emit("Cancelling worker pool...")
        
        for worker in self.workers:
            worker.stop()
        
        for thread in self.threads:
            if thread.isRunning():
                thread.quit()
                # thread.wait(1000) # Don't block UI too long

