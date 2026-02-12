"""
Multi-threaded Downloader Worker with SQLite persistence.
"""

import os
import time
import shutil
from pathlib import Path
from typing import List, Optional, Dict
import requests

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QRunnable, QThreadPool, QMutex, QMutexLocker, pyqtSlot

from core.scraped_data import ScrapedData, ResourceCategory
from core.models import Resource, ResourceType
from core.database import DatabaseManager
from utils.sanitizer import sanitize_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DownloaderSignals(QObject):
    """Signals for the downloader worker."""
    started = pyqtSignal()
    # Throttled progress: (downloaded_count, total_count)
    progress = pyqtSignal(int, int)
    overall_progress = pyqtSignal(int, int)
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
        temp_path = None
        
        # Retry configuration
        max_retries = 3
        retry_delay = 2 # seconds
        
        for attempt in range(max_retries + 1):
            try:
                # Determine filename
                filename = self._get_filename()
                filepath = Path(self.output_dir) / filename
                filepath = self._ensure_unique(filepath)
                local_path = str(filepath)
                temp_path = filepath.with_suffix(filepath.suffix + ".tmp")

                # Check if this resource needs download (skip if content exists)
                if self.resource.content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(self.resource.content)
                    success = True
                    file_size = len(self.resource.content.encode('utf-8'))
                    break # Success
                else:
                    # Optimized Network Download with Smart Skip
                    
                    # 1. Check if file exists locally
                    if filepath.exists() and filepath.stat().st_size > 0:
                        local_size = filepath.stat().st_size
                        try:
                            # 2. Perform HEAD request to get remote size
                            head = requests.head(url, headers=self.headers, timeout=10, allow_redirects=True)
                            remote_size = int(head.headers.get('content-length', 0))
                            
                            if remote_size > 0 and abs(remote_size - local_size) < 100:
                                if remote_size == local_size:
                                    logger.info(f"Skipping {filename} (Already exists, size matches)")
                                    success = True
                                    file_size = local_size
                                    local_path = str(filepath)
                                    # Early return/update
                                    self.db.update_resource_status(
                                        task_id=self.task_id,
                                        url=url, 
                                        status="completed", 
                                        local_path=local_path,
                                        file_size=file_size,
                                        error="Skipped (cached)"
                                    )
                                    if self.callback:
                                        self.callback(True, url, "Skipped (cached)")
                                    return
                        except:
                            pass # Head failed, proceed to download


                    # 3. Check for Data URI
                    if url.startswith('data:'):
                        try:
                            import base64
                            header, encoded = url.split(",", 1)
                            data = base64.b64decode(encoded)
                            
                            with open(filepath, 'wb') as f:
                                f.write(data)
                                
                            success = True
                            file_size = len(data)
                            break
                        except Exception as e:
                            logger.error(f"Failed to decode data URI: {e}")
                            # Fallthrough to fail

                    # 4. Check Disk Space
                    if not self._check_disk_space(Path(self.output_dir), 10 * 1024 * 1024): # Min 10MB check + size later
                         raise IOError("Insufficient disk space")

                    # 4. Stream download
                    with requests.get(url, headers=self.headers, stream=True, timeout=60) as r:
                         r.raise_for_status()
                         file_size = int(r.headers.get('content-length', 0))
                         
                         # Check space again if we know the size
                         if file_size > 0 and not self._check_disk_space(Path(self.output_dir), file_size):
                             raise IOError(f"Insufficient disk space for {file_size} bytes")
                         
                         with open(temp_path, 'wb') as f:
                             for chunk in r.iter_content(chunk_size=8192):
                                 if chunk:
                                     f.write(chunk)
                    
                    # Rename on success
                    if filepath.exists():
                        filepath.unlink()
                    temp_path.rename(filepath)
                    
                    success = True
                    break # Success, exit retry loop
                    
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Download attempt {attempt+1}/{max_retries+1} failed for {url}: {e}")
                
                # Cleanup temp
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except: pass
                
                if attempt < max_retries:
                    time.sleep(retry_delay * (attempt + 1)) # Exponential backoff
                else:
                    success = False
                    logger.error(f"Download finally failed {url}: {e}")

        # Update DB
        status = "completed" if success else "failed"
        self.db.update_resource_status(
            task_id=self.task_id,
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
        # Check for data URI mime type
        if url.startswith('data:'):
            try:
                mime = url.split(';')[0].split(':')[1]
                import mimetypes
                ext = mimetypes.guess_extension(mime)
                if ext: return ext
            except:
                pass

        ext = os.path.splitext(url)[1]
        if not ext:
            if self.resource.resource_type == ResourceType.IMAGE:
                return ".jpg"
            if self.resource.resource_type in (ResourceType.VIDEO, ResourceType.M3U8):
                return ".mp4"
            if self.resource.resource_type == ResourceType.AUDIO:
                return ".mp3"
            if self.resource.resource_type in (ResourceType.TEXT, ResourceType.JSON_DATA, ResourceType.RICH_TEXT):
                return ".txt"
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

    def _check_disk_space(self, path: Path, required_bytes: int) -> bool:
        try:
            check_path = path if path.exists() else path.parent
            if not check_path.exists(): check_path = Path('.')
            total, used, free = shutil.disk_usage(check_path)
            # Reserve 50MB
            return free > (required_bytes + 50 * 1024 * 1024)
        except:
            return True

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
        task_id = -1
        try:
            self.signals.started.emit()
            self.signals.log.emit(f"🚀 Starting batch download (Threads: {self.max_workers})")
            
            task_id = self.db.create_task(self.scraped_data.source_url, self.output_dir)
            
            resources: List[Resource] = []
            for cat in self.selected_categories:
                resources.extend(self.scraped_data.get_resources_by_category(cat))
                
            self._total_tasks = len(resources)
            if self._total_tasks == 0:
                self.signals.log.emit("⚠️ No resources selected.")
                self.signals.finished.emit(0, 0)
                if task_id != -1:
                    self.db.update_task_status(task_id, "completed", finished=True)
                return

            os.makedirs(self.output_dir, exist_ok=True)
            
            headers = {
                'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'Referer': self.scraped_data.source_url
            }

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
                
            self.pool.waitForDone()
            
            status = "cancelled" if self._is_cancelled else "completed"
            if task_id != -1:
                self.db.update_task_status(task_id, status, finished=True)
                self.db.update_task_progress(task_id, self._success_count, self._total_tasks)
            
            self.signals.finished.emit(self._success_count, self._total_tasks)
            self.signals.log.emit(f"✅ Job {status}. Success: {self._success_count}/{self._total_tasks}")
        except Exception as e:
            logger.exception("DownloaderWorker crashed")
            self.signals.error.emit(str(e))
            if task_id != -1:
                try:
                    self.db.update_task_status(task_id, "failed", finished=True)
                except Exception:
                    logger.exception("Failed to mark task failed")
            self.signals.finished.emit(self._success_count, self._total_tasks)

    def cancel(self):
        self._is_cancelled = True
        self.pool.clear() # Clear queue
        # Note: Running tasks cannot be killed easily in QThreadPool without flags in Runnable
        # We rely on existing tasks finishing or checking cancellation if we shared the flag (we didnt here for simplicity)
        
    def _on_item_finished(self, success: bool, url: str, error: str):
        """Callback from Runnable (called from worker thread)."""
        try:
            if self._is_cancelled:
                return

            with QMutexLocker(self._mutex):
                self._completed_tasks += 1
                if success:
                    self._success_count += 1
                    
            self.signals.progress.emit(self._completed_tasks, self._total_tasks)
            self.signals.overall_progress.emit(self._completed_tasks, self._total_tasks)
            if not success:
                self.signals.file_log.emit(f"❌ Failed: {os.path.basename(url)} ({error})")
            else:
                self.signals.file_log.emit(f"✓ Downloaded: {os.path.basename(url)}")
        except Exception:
            logger.exception("Downloader callback error")
        # else:
        #     self.signals.file_log.emit(f"✓ Downloaded: {os.path.basename(url)}")
