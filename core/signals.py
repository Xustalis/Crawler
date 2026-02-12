from PyQt6.QtCore import QObject, pyqtSignal

class WorkerSignals(QObject):
    """
    Signals for individual RequestWorker.
    Must be a QObject to support signals.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    task_started = pyqtSignal(str)
    # url, resources, links, depth
    task_completed = pyqtSignal(str, list, list, int)
    # url, error
    task_failed = pyqtSignal(str, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal()

class PoolSignals(QObject):
    """
    Signals for WorkerPool.
    """
    started = pyqtSignal()
    progress = pyqtSignal(int, int)  # completed, total
    finished = pyqtSignal(object)    # ScrapedData
    results_updated = pyqtSignal(object) # ScrapedData
    log_message = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

