"""
Refactored Worker using QObject + QThread pattern for better signal handling and stability.
"""

import time
import random
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.crawl_queue import CrawlTask
from core.parser import PageParser
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RequestWorker(QObject):
    """
    Worker object that processes crawl tasks.
    Designed to be moved to a QThread.
    """
    
    # Signals
    task_started = pyqtSignal(str)
    task_completed = pyqtSignal(str, list, list, int)
    task_failed = pyqtSignal(str, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal() # Emitted when loop ends
    
    def __init__(self, worker_id: int, crawl_queue):
        super().__init__()
        self.worker_id = worker_id
        self.crawl_queue = crawl_queue
        self._is_running = True
        self.parser = PageParser()  # Uses NetworkManager internally
    
    @pyqtSlot()
    def process_queue(self):
        """Main processing loop."""
        self.log_message.emit(f"Worker {self.worker_id} started (Async)")
        
        while self._is_running:
            try:
                # Use a smaller timeout to check for cancellation frequently
                task: Optional[CrawlTask] = self.crawl_queue.get(block=True, timeout=0.5)
                
                if task is None:
                    # Timeout
                    if self.crawl_queue.is_empty() and not self._is_running:
                        break
                    continue
                
                self._process_task(task)
                
            except Exception as e:
                # Catch queue errors
                pass
                
        self.log_message.emit(f"Worker {self.worker_id} stopped")
        self.finished.emit()

    def _process_task(self, task: CrawlTask):
        try:
            self.task_started.emit(task.url)
            
            # Random delay
            # delay = random.uniform(0.1, 0.5)
            # time.sleep(delay)
            # Remove artificial sleep for performance
            pass
            
            # Parse using robust parser
            resources, links = self.parser.parse(task.url)
            
            # Success
            self.task_completed.emit(task.url, resources, links, task.depth)
            self.crawl_queue.task_done(success=True)
            
            logger.debug(f"Worker {self.worker_id}: Parsed {task.url}")
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed: {e}", exc_info=True)
            self.task_failed.emit(task.url, str(e))
            self.crawl_queue.task_done(success=False)

    def stop(self):
        """Signal worker to stop."""
        self._is_running = False

