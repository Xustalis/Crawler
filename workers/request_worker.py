"""
Refactored Worker using QRunnable + QThreadPool pattern for better stability.
"""

import time
import random
from typing import Optional

from PyQt6.QtCore import QRunnable, pyqtSlot, QObject

from core.crawl_queue import CrawlTask
from core.parser import PageParser
from core.signals import WorkerSignals
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RequestWorker(QRunnable):
    """
    Worker object that processes crawl tasks.
    Designed to be run in a QThreadPool.
    """
    
    def __init__(self, worker_id: int, crawl_queue, signals: WorkerSignals):
        super().__init__()
        self.worker_id = worker_id
        self.crawl_queue = crawl_queue
        self.signals = signals
        self._is_running = True
        self.parser = PageParser()  # Uses NetworkManager internally
        
    @pyqtSlot()
    def run(self):
        """Main processing loop."""
        try:
            self.signals.log_message.emit(f"Worker {self.worker_id} started (Async)")
        except RuntimeError:
            pass

        
        while self._is_running:
            # Check for interruption is different in QRunnable
            # We rely on _is_running flag being set by manager
            
            try:
                # Use a smaller timeout to check for cancellation frequently
                task: Optional[CrawlTask] = self.crawl_queue.get(block=True, timeout=0.5)
                
                if task is None:
                    # Timeout
                    if self.crawl_queue.is_empty():
                        # If queue is empty, we might want to exit or wait?
                        # In pool model, workers usually stay alive until cancelled or finished.
                        # But here we let them spin with timeout.
                        if not self._is_running:
                            break
                    continue
                
                if not self._is_running:
                    # Put back task? Or just process it?
                    # If we picked it up, better process it unless critical stop.
                    self._process_task(task)
                    break 

                self._process_task(task)
                
            except Exception as e:
                logger.exception(f"Worker {self.worker_id} loop error: {e}")
        
        # Defensive teardown: WorkerPool might be destroyed before we finish
        try:
            if self.signals:
                self.signals.log_message.emit(f"Worker {self.worker_id} stopped")
                self.signals.finished.emit()
        except RuntimeError:
            pass # Object deleted, ignore
        except Exception as e:
            logger.error(f"Worker {self.worker_id} teardown error: {e}")




    def _process_task(self, task: CrawlTask):
        try:
            # Safe start emission
            try:
                self.signals.task_started.emit(task.url)
            except RuntimeError:
                pass

            # Remove artificial sleep for performance
            
            # Parse using robust parser
            resources, links = self.parser.parse(task.url)
            
            # Safe completion emission
            try:
                self.signals.task_completed.emit(task.url, resources, links, task.depth)
            except RuntimeError:
                pass
            
            self.crawl_queue.task_done(success=True)
            logger.debug(f"Worker {self.worker_id}: Parsed {task.url}")
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed: {e}", exc_info=True)
            # Safe failure emission
            try:
                self.signals.task_failed.emit(task.url, str(e))
            except RuntimeError:
                pass
            self.crawl_queue.task_done(success=False)





    def stop(self):
        """Signal worker to stop."""
        self._is_running = False
