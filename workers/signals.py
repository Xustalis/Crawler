"""
PyQt6 signal definitions for thread-safe communication.

All signals are defined in a central location to maintain clarity
and ensure type safety.
"""

from PyQt6.QtCore import QObject, pyqtSignal

from core.models import Resource


class CrawlerSignals(QObject):
    """
    Signal definitions for CrawlerWorker.
    
    All communication between worker thread and UI thread
    must go through these signals.
    """
    
    # Analysis phase signals
    analysis_started = pyqtSignal()  # Emitted when URL analysis begins
    analysis_progress = pyqtSignal(str)  # Emitted with status message
    resources_found = pyqtSignal(list)  # Emitted with List[Resource]
    analysis_completed = pyqtSignal()  # Emitted when analysis finishes
    
    # Download phase signals
    download_started = pyqtSignal(Resource)  # Emitted when downloading a resource
    download_progress = pyqtSignal(Resource, float)  # Emitted with (resource, progress 0.0-1.0)
    download_completed = pyqtSignal(Resource)  # Emitted when a resource completes
    download_failed = pyqtSignal(Resource, str)  # Emitted with (resource, error_message)
    
    # Merging phase signals (for M3U8)
    merging_started = pyqtSignal(Resource)  # Emitted when FFmpeg merge starts
    merging_completed = pyqtSignal(Resource)  # Emitted when merge completes
    
    # Overall progress
    overall_progress = pyqtSignal(int, int)  # Emitted with (completed, total)
    
    # Log messages
    log_message = pyqtSignal(str)  # Thread-safe logging to UI
    
    # Error handling
    error_occurred = pyqtSignal(str)  # Critical errors
    
    # Task completion
    task_finished = pyqtSignal()  # Emitted when all work is done
