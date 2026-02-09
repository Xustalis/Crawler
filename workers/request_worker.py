"""
Individual worker thread for concurrent crawling.

Each worker pulls tasks from the shared queue, fetches pages,
parses content, and emits results via signals.
"""

import time
import random
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from core.crawl_queue import CrawlTask
from core.parser import PageParser
from core.models import Resource
from utils.logger import setup_logger


logger = setup_logger(__name__)


class RequestWorker(QThread):
    """
    Worker thread that processes crawl tasks from queue.
    
    Each worker maintains its own Session for connection pooling
    and adds random delays to avoid overwhelming servers.
    """
    
    # Signals
    task_started = pyqtSignal(str)  # url
    task_completed = pyqtSignal(str, list, list)  # url, resources, links
    task_failed = pyqtSignal(str, str)  # url, error
    log_message = pyqtSignal(str)
    
    def __init__(self, worker_id: int, crawl_queue, parent=None):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique worker identifier
            crawl_queue: Shared CrawlQueue instance
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.worker_id = worker_id
        self.crawl_queue = crawl_queue
        self._is_cancelled = False
        
        # Each worker has its own parser (with its own Session)
        self.parser = PageParser()
    
    def run(self) -> None:
        """Main worker loop - pulls tasks and processes them."""
        self.log_message.emit(f"Worker {self.worker_id} started")
        
        while not self._is_cancelled:
            # Get task from queue (block for 1 second)
            task: Optional[CrawlTask] = self.crawl_queue.get(block=True, timeout=1.0)
            
            if task is None:
                # Timeout - check if queue is empty
                if self.crawl_queue.is_empty():
                    break  # No more work
                continue
            
            # Process task
            try:
                self.task_started.emit(task.url)
                
                # Random delay (0.1-0.5s) to avoid hammering server
                delay = random.uniform(0.1, 0.5)
                time.sleep(delay)
                
                # Parse page
                resources, links = self.parser.parse(task.url)
                
                # Success
                self.task_completed.emit(task.url, resources, links)
                self.crawl_queue.task_done(success=True)
                
                logger.debug(f"Worker {self.worker_id}: Parsed {task.url} - {len(resources)} resources, {len(links)} links")
                
            except Exception as e:
                error_msg = f"Worker {self.worker_id} failed on {task.url}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                self.task_failed.emit(task.url, str(e))
                self.crawl_queue.task_done(success=False)
        
        self.log_message.emit(f"Worker {self.worker_id} stopped")
    
    def cancel(self):
        """Request worker to stop."""
        self._is_cancelled = True
