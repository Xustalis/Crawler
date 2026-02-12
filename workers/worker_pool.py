"""
Worker pool manager for concurrent crawling using QThreadPool.
"""

from typing import List, Optional
from PyQt6.QtCore import QObject, QThreadPool

from core.crawl_queue import CrawlQueue, CrawlTask, Priority
from core.scraped_data import ScrapedData
from core.models import Resource, ResourceType
from workers.request_worker import RequestWorker
from core.database import DatabaseManager
from core.signals import PoolSignals, WorkerSignals
from utils.logger import setup_logger


logger = setup_logger(__name__)


class WorkerPool(QObject):
    """
    Manages a pool of concurrent RequestWorker runnables.
    Coordinates task distribution, result aggregation, and progress reporting.
    """
    
    def __init__(self, num_workers: int = 5, max_depth: int = 2):
        super().__init__()
        
        # Signals
        self.signals = PoolSignals()
        
        self.num_workers = min(max(1, num_workers), 20)  # Clamp to 1-20
        self.max_depth = max_depth
        
        # Queue and ThreadPool
        self.crawl_queue = CrawlQueue()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(self.num_workers)
        
        self.workers: List[RequestWorker] = []
        
        # Results aggregation
        self.scraped_data: Optional[ScrapedData] = None
        
        # Database
        self.db = DatabaseManager()
        self.task_id = -1
        
        # State
        self._is_cancelled = False
    
    def start_crawl(self, seed_url: str, auto_concurrency: bool = False):
        self._is_cancelled = False
        self.auto_concurrency = auto_concurrency
        
        # Initialize ScrapedData
        self.scraped_data = ScrapedData(source_url=seed_url)
        
        # Create Task in DB
        self.task_id = self.db.create_task(seed_url, save_path="[SCAN ONLY]")
        self.db.update_task_status(self.task_id, "scanning")
        
        # Add seed task
        seed_task = CrawlTask(url=seed_url, depth=1, priority=Priority.HIGH)
        self.crawl_queue.put(seed_task)
        
        self._pool_finished_emitted = False
        
        # Create and start workers
        self._spawn_workers(self.num_workers)
        
        # Start Auto-Concurrency Timer
        if self.auto_concurrency:
            from PyQt6.QtCore import QTimer
            self.adjust_timer = QTimer()
            self.adjust_timer.timeout.connect(self._adjust_concurrency)
            self.adjust_timer.start(2000) # Check every 2s

        self.signals.started.emit()
        self.signals.log_message.emit(f"Started {self.num_workers} workers for {seed_url} (Auto: {auto_concurrency})")
    
    def _spawn_workers(self, count: int):
        current_count = len(self.workers)
        # Check if we already have enough active workers?
        # QThreadPool manages threads, we just manage Runnable tasks.
        # But our Runnables are long-running loops.
        
        for i in range(count):
            if len(self.workers) >= 20: break
            
            w_id = len(self.workers) + 1
            

            # Create per-worker signals (linked to our slots)
            w_signals = WorkerSignals(parent=self)
            w_signals.task_completed.connect(self._on_task_completed)
            w_signals.task_failed.connect(self._on_task_failed)
            # Use a slot instead of direct signal-to-signal connection to avoid meta-object issues
            w_signals.log_message.connect(self._on_worker_log)
            # w_signals.finished.connect(...) # Can handle worker finish if needed
            
            worker = RequestWorker(worker_id=w_id, crawl_queue=self.crawl_queue, signals=w_signals)
            self.workers.append(worker)
            self.pool.start(worker)

    def _on_worker_log(self, message: str):
        """Handle log messages from workers safely."""
        if hasattr(self, 'signals') and hasattr(self.signals, 'log_message'):
            self.signals.log_message.emit(message)

            
    def _adjust_concurrency(self):
        """Dynamically adjust worker count based on queue size."""
        q_size = self.crawl_queue.size()
        
        if q_size > 50 and len(self.workers) < 20:
            new_workers = min(5, 20 - len(self.workers))
            if new_workers > 0:
                self.signals.log_message.emit(f"Scale UP: Adding {new_workers} workers (Queue: {q_size})")
                self._spawn_workers(new_workers)
                
    def _on_task_started(self, url: str):
        stats = self.crawl_queue.get_stats()
        self.signals.progress.emit(stats['completed'], stats['total_queued'])
    
    def _on_task_completed(self, url: str, resources: List[Resource], links: List[str], depth: int):
        if self._is_cancelled: return

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
        
        # Queue links
        for link in links:
            if depth < self.max_depth:
                next_depth = depth + 1
                next_task = CrawlTask(url=link, depth=next_depth, priority=Priority.NORMAL, referer=url)
                self.crawl_queue.put(next_task)
        
        stats = self.crawl_queue.get_stats()
        self.signals.progress.emit(stats['completed'], stats['total_queued'])
        self.signals.log_message.emit(f"Completed {url}: {len(resources)} resources")

        if self.scraped_data is not None:
            self.signals.results_updated.emit(self.scraped_data)
        
        self._check_finish_condition()

    def _on_task_failed(self, url: str, error: str):
        if self._is_cancelled: return
        self.signals.log_message.emit(f"Failed {url}: {error}")
        stats = self.crawl_queue.get_stats()
        self.signals.progress.emit(stats['completed'], stats['total_queued'])
        if self.scraped_data is not None:
            self.signals.results_updated.emit(self.scraped_data)
        self._check_finish_condition()

    def _check_finish_condition(self):
        if self.crawl_queue.is_empty() and self.crawl_queue.get_stats()['pending'] == 0:
             # Check unfinished tasks in queue
             if self.crawl_queue._queue.unfinished_tasks == 0:
                 self._finalize_pool()

    def _finalize_pool(self):
        if self._pool_finished_emitted:
            return
        self._pool_finished_emitted = True
        
        if hasattr(self, 'adjust_timer'):
            self.adjust_timer.stop()
            
        self.signals.log_message.emit("All tasks completed.")
        
        # DB Update
        total_items = (len(self.scraped_data.images) + len(self.scraped_data.videos) + 
                      len(self.scraped_data.m3u8_streams) + len(self.scraped_data.documents) + 
                      len(self.scraped_data.audios))

        try:
            for res in (
                self.scraped_data.images
                + self.scraped_data.videos
                + self.scraped_data.m3u8_streams
                + self.scraped_data.documents
                + self.scraped_data.audios
            ):
                self.db.add_resource(self.task_id, res)
        except Exception:
            logger.exception("Failed to persist scanned resources")
                      
        self.db.update_task_progress(self.task_id, 0, total_items)
        self.db.update_task_status(self.task_id, "scanned", finished=True)
        
        self.signals.finished.emit(self.scraped_data)
        self.cancel(wait=False)

    def cancel(self, wait: bool = False, timeout_ms: int = 2000):
        self._is_cancelled = True
        if hasattr(self, 'adjust_timer'):
            self.adjust_timer.stop()

        self.signals.log_message.emit("Cancelling worker pool...")
        
        # Set flags on workers
        for worker in self.workers:
            worker.stop()
            
        # Clear queue
        self.crawl_queue.clear()
        
        self.pool.clear() # Removes queued tasks that haven't started
        
        if wait:
            self.pool.waitForDone(timeout_ms)
