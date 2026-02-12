"""
Thread-safe crawl queue for producer-consumer pattern.

Manages URLs to be crawled with priority support and statistics tracking.
"""

import queue
import threading
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum


class Priority(IntEnum):
    """Task priority levels (lower number = higher priority)."""
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class CrawlTask:
    """Represents a single crawl task."""
    url: str
    depth: int
    priority: Priority = Priority.NORMAL
    referer: Optional[str] = None


class CrawlQueue:
    """
    Thread-safe queue for managing crawl tasks.
    
    Uses priority queue internally to support depth-first or breadth-first
    crawling strategies.
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize crawl queue.
        
        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue = queue.PriorityQueue(maxsize=maxsize)
        self._lock = threading.Lock()
        
        # Statistics
        self._total_queued = 0
        self._total_completed = 0
        self._total_failed = 0
        self._visited_urls = set()
    
    def put(self, task: CrawlTask, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Add task to queue.
        
        Args:
            task: CrawlTask to add
            block: Block if queue is full
            timeout: Timeout for blocking
            
        Returns:
            True if task was added, False if already visited or queue full
        """
        with self._lock:
            # Deduplication
            if task.url in self._visited_urls:
                return False
            
            self._visited_urls.add(task.url)
        
        try:
            # Priority queue expects (priority, item)
            self._queue.put((task.priority, task), block=block, timeout=timeout)
            
            with self._lock:
                self._total_queued += 1
            
            return True
            
        except queue.Full:
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[CrawlTask]:
        """
        Get next task from queue.
        
        Args:
            block: Block if queue is empty
            timeout: Timeout for blocking
            
        Returns:
            Next CrawlTask or None if queue is empty
        """
        try:
            priority, task = self._queue.get(block=block, timeout=timeout)
            return task
        except queue.Empty:
            return None
    
    def task_done(self, success: bool = True):
        """
        Mark a task as completed.
        
        Args:
            success: Whether task completed successfully
        """
        with self._lock:
            if success:
                self._total_completed += 1
            else:
                self._total_failed += 1
        
        self._queue.task_done()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def get_stats(self) -> dict:
        """
        Get queue statistics.
        
        Returns:
            Dict with queued, completed, failed, pending counts
        """
        with self._lock:
            return {
                'total_queued': self._total_queued,
                'completed': self._total_completed,
                'failed': self._total_failed,
                'pending': self._queue.qsize(),
                'visited': len(self._visited_urls)
            }
    
    def clear(self):
        """Clear all tasks from queue."""
        with self._queue.mutex:
            self._queue.queue.clear()
        
        with self._lock:
            self._visited_urls.clear()
            self._total_queued = 0
            self._total_completed = 0
            self._total_failed = 0
