import sys
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication

class Worker(QObject):
    log_message = pyqtSignal(str)
    
    def run(self):
        self.log_message.emit("Test message")

class Pool(QObject):
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.worker = Worker()
        # This mirrors the code in WorkerPool
        self.worker.log_message.connect(self.log_message.emit)
    
    def run(self):
        self.worker.run()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        pool = Pool()
        pool.log_message.connect(lambda msg: print(f"Received: {msg}"))
        pool.run()
        print("Success")
    except Exception as e:
        print(f"Failed: {e}")
