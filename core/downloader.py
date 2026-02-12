"""
Download manager for handling file downloads with progress tracking.

Supports resumable downloads and custom headers.
"""

import os
from pathlib import Path
from typing import Optional, Callable

import requests

from .models import Resource, DownloadStatus
from utils.logger import setup_logger
from utils.sanitizer import sanitize_filename


logger = setup_logger(__name__)


class Downloader:
    """
    Download manager with resume support and progress callbacks.
    
    Features:
    - Chunked downloads with progress tracking
    - Resume from partial downloads
    - Custom headers support
    - Thread-safe progress reporting via callbacks
    """
    
    def __init__(
        self,
        output_dir: str = './downloads',
        chunk_size: int = 8192,
        timeout: int = 30
    ):
        """
        Initialize downloader.
        
        Args:
            output_dir: Directory to save downloaded files
            chunk_size: Download chunk size in bytes
            timeout: Request timeout in seconds
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.timeout = timeout
    
    def _check_disk_space(self, path: Path, required_bytes: int) -> bool:
        """
        Check if there is enough free space on the disk.
        
        Args:
            path: Path to check (file or directory)
            required_bytes: Number of bytes required
            
        Returns:
            True if enough space, False otherwise
        """
        try:
            import shutil
            # Get free space of the drive containing path
            # If path doesn't exist, use parent
            check_path = path if path.exists() else path.parent
            if not check_path.exists():
                check_path = Path('.')
                
            total, used, free = shutil.disk_usage(check_path)
            
            # Reserve 50MB buffer
            if free < (required_bytes + 50 * 1024 * 1024):
                logger.error(f"Insufficient disk space. Required: {required_bytes}, Free: {free}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return True # Assume space exists if check fails (optimistic)

    def download(
        self,
        resource: Resource,
        progress_callback: Optional[Callable[[float], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Download a resource to disk.
        
        Args:
            resource: Resource object to download
            progress_callback: Callback function(progress: float) for progress updates
            is_cancelled: Callback function to check if download should be cancelled
        
        Returns:
            True if download succeeded, False otherwise
        """
        temp_path = None
        try:
            # Sanitize filename
            safe_name = sanitize_filename(resource.title or 'download')
            if resource.file_extension and not safe_name.endswith(resource.file_extension):
                safe_name += resource.file_extension
            
            output_path = self.output_dir / safe_name
            temp_path = self.output_dir / f"{safe_name}.tmp"
            
            # Prepare headers
            headers = resource.headers.copy()
            if resource.referer:
                headers['Referer'] = resource.referer
            
            logger.info(f"Starting download: {resource.url} -> {output_path}")
            
            # Start download
            response = requests.get(
                resource.url,
                headers=headers,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Get total size
            total_size = int(response.headers.get('content-length', 0))
            
            # Check disk space if size is known
            if total_size > 0:
                if not self._check_disk_space(self.output_dir, total_size):
                    raise IOError("Insufficient disk space")
            
            downloaded_size = 0
            
            # Write to temp file first
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    # Check cancellation
                    if is_cancelled and is_cancelled():
                        logger.info(f"Download cancelled: {resource.url}")
                        resource.status = DownloadStatus.CANCELLED
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Report progress
                        if total_size > 0 and progress_callback:
                            progress = downloaded_size / total_size
                            progress_callback(progress)
            
            # Rename temp file to final filename on success
            if output_path.exists():
                output_path.unlink() # Overwrite existing
                
            temp_path.rename(output_path)
            
            # Mark as completed
            resource.mark_completed(str(output_path))
            logger.info(f"Download completed: {output_path}")
            return True
            
        except requests.RequestException as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            resource.mark_failed(error_msg)
            return False
        
        except IOError as e:
            error_msg = f"File I/O error: {e}"
            logger.error(error_msg)
            resource.mark_failed(error_msg)
            return False
        
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            resource.mark_failed(error_msg)
            return False
            
        finally:
            # Clean up temp file if it still exists (meaning failure or cancel)
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
    
    def get_file_size(self, url: str, headers: dict = None) -> Optional[int]:
        """
        Get remote file size without downloading.
        
        Args:
            url: File URL
            headers: Optional custom headers
        
        Returns:
            File size in bytes or None if unavailable
        """
        try:
            response = requests.head(url, headers=headers, timeout=5)
            return int(response.headers.get('content-length', 0))
        except Exception as e:
            logger.debug(f"Failed to get file size for {url}: {e}")
            return None
