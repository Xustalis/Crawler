"""
Multi-threaded Downloader Worker with SQLite persistence.
"""

import os
import time
from pathlib import Path
from typing import List, Optional, Dict
import requests

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QRunnable, QThreadPool, QMutex, QMutexLocker, pyqtSlot

from core.scraped_data import ScrapedData, ResourceCategory
from core.models import Resource
from core.database import DatabaseManager
from utils.sanitizer import sanitize_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DownloaderSignals(QObject):
    """Signals for the downloader worker."""
    started = pyqtSignal()
    # Throttled progress: (downloaded_count, total_count)
    progress = pyqtSignal(int, int)
    # File completion (active logging)
    file_log = pyqtSignal(str) # e.g. "Downloaded: image.jpg"
    finished = pyqtSignal(int, int) # success, total
    error = pyqtSignal(str)
    log = pyqtSignal(str)

class DownloadRunnable(QRunnable):
    """
    Worker task for downloading a single file.
    """
    def __init__(self, resource: Resource, output_dir: str, task_id: int, db_mgr: DatabaseManager, headers: dict):
        super().__init__()
        self.resource = resource
        self.output_dir = output_dir
        self.task_id = task_id
        self.db = db_mgr
        self.headers = headers
        self.signals = None # To be set by manager if needed, but we use callbacks usually
        self.callback = None # Function to call on finish (success, filename, error)

    def set_callback(self, callback):
        self.callback = callback

    def run(self):
        url = self.resource.url
        success = False
        error_msg = None
        local_path = ""
        file_size = 0
        
        try:
            # Determine filename
            filename = self._get_filename()
            filepath = Path(self.output_dir) / filename
            filepath = self._ensure_unique(filepath)
            local_path = str(filepath)

            # Check if this resource needs download (skip if content exists)
            if self.resource.content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.resource.content)
                success = True
                file_size = len(self.resource.content.encode('utf-8'))
            else:
                # Network Download
                with requests.get(url, headers=self.headers, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    file_size = int(r.headers.get('content-length', 0))
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                success = True

        except Exception as e:
            error_msg = str(e)
            success = False
            # logger.error(f"Download failed {url}: {e}")

        # Update DB
        status = "completed" if success else "failed"
        self.db.update_resource_status(
            url=url, 
            status=status, 
            local_path=local_path if success else None,
            file_size=file_size,
            error=error_msg
        )

        if self.callback:
            self.callback(success, url, error_msg)

    def _get_filename(self) -> str:
        # Similar logic to original but robust
        from urllib.parse import urlparse, unquote
        import hashlib
        
        # Try title first
        if self.resource.title and len(self.resource.title) < 100:
             # Basic check to avoid "Page Content" generic titles if possible, or just use it
             name = sanitize_filename(self.resource.title)
             # Add extension if missing
             if '.' not in name:
                 ext = self._guess_extension(self.resource.url)
                 name += ext
             return name

        # Fallback to URL path
        try:
            parsed = urlparse(self.resource.url)
            path = unquote(parsed.path)
            name = os.path.basename(path)
            if not name or len(name) > 100:
                raise ValueError("Invalid name")
            return sanitize_filename(name)
        except:
            hash_name = hashlib.md5(self.resource.url.encode()).hexdigest()[:10]
            ext = self._guess_extension(self.resource.url)
            return f"file_{hash_name}{ext}"

    def _guess_extension(self, url: str) -> str:
        ext = os.path.splitext(url)[1]
        if not ext:
            if self.resource.resource_type == ResourceCategory.IMAGES: return ".jpg"
            if self.resource.resource_type == ResourceCategory.VIDEOS: return ".mp4"
            return ".dat"
        return ext

    def _ensure_unique(self, path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

class DownloaderWorker(QThread):
    """
    Manager Thread for Batch Downloads.
    Spawns tasks to QThreadPool and aggregates results.
    """
    def __init__(
        self,
        scraped_data: ScrapedData,
        selected_categories: List[ResourceCategory],
        output_dir: str,
        max_workers: int = 5
    ):
        super().__init__()
        self.scraped_data = scraped_data
        self.selected_categories = selected_categories
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.signals = DownloaderSignals()
        
        self.db = DatabaseManager()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max_workers)
        
        self._is_cancelled = False
        self._total_tasks = 0
        self._completed_tasks = 0
        self._success_count = 0
        
        # Mutex for thread-safe counter updates
        self._mutex = QMutex()

    def run(self):
        self.signals.started.emit()
        self.signals.log.emit(f"🚀 Starting batch download (Threads: {self.max_workers})")
        
        # 1. Create Task in DB
        task_id = self.db.create_task(self.scraped_data.source_url, self.output_dir)
        
        # 2. Filter resources
        resources = []
        for cat in self.selected_categories:
            resources.extend(self.scraped_data.get_resources_by_category(cat))
            
        self._total_tasks = len(resources)
        if self._total_tasks == 0:
            self.signals.log.emit("⚠️ No resources selected.")
            self.signals.finished.emit(0, 0)
            self.db.update_task_status(task_id, "completed", finished=True)
            return

        # 3. Queue Jobs
        os.makedirs(self.output_dir, exist_ok=True)
        
        headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            'Referer': self.scraped_data.source_url
        }

        # First, register all resources in DB
        self.signals.log.emit("📝 Registering tasks in database...")
        for res in resources:
            self.db.add_resource(task_id, res)

        self.signals.log.emit("⬇️ dispatching download jobs...")
        
        for res in resources:
            if self._is_cancelled:
                break
                
            runnable = DownloadRunnable(res, self.output_dir, task_id, self.db, headers)
            runnable.set_callback(self._on_item_finished)
            self.pool.start(runnable)
            
        # Wait for completion
        self.pool.waitForDone()
        
        # Final update
        status = "cancelled" if self._is_cancelled else "completed"
        self.db.update_task_status(task_id, status, finished=True)
        self.db.update_task_progress(task_id, self._success_count, self._total_tasks)
        
        self.signals.finished.emit(self._success_count, self._total_tasks)
        self.signals.log.emit(f"✅ Job {status}. Success: {self._success_count}/{self._total_tasks}")

    def cancel(self):
        self._is_cancelled = True
        self.pool.clear() # Clear queue
        # Note: Running tasks cannot be killed easily in QThreadPool without flags in Runnable
        # We rely on existing tasks finishing or checking cancellation if we shared the flag (we didnt here for simplicity)
        
    def _on_item_finished(self, success: bool, url: str, error: str):
        """Callback from Runnable (called from worker thread)."""
        if self._is_cancelled:
            return

        with QMutexLocker(self._mutex):
            self._completed_tasks += 1
            if success:
                self._success_count += 1
                
        # Emit signal
        # Note: If high frequency, we might want to throttle this.
        # For now, emitting every time is okay for < 1000 items.
        self.signals.progress.emit(self._completed_tasks, self._total_tasks)
        if not success:
            self.signals.file_log.emit(f"❌ Failed: {os.path.basename(url)} ({error})")
        # else:
        #     self.signals.file_log.emit(f"✓ Downloaded: {os.path.basename(url)}")
