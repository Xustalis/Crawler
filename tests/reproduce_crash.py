
import sys
import time
from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable, QCoreApplication

# Define signals similar to the application
class WorkerSignals(QObject):
    log_message = pyqtSignal(str)

class PoolSignals(QObject):
    log_message = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals

    def run(self):
        # Simulate work and emit signal
        try:
            for i in range(10):
                self.signals.log_message.emit(f"Log message {i}")
                time.sleep(0.01)
        except Exception as e:
            print(f"Worker exception: {e}")

class Manager(QObject):
    def __init__(self):
        super().__init__()
        self.signals = PoolSignals()
        self.pool = QThreadPool()
        self.finished_count = 0

    def start(self):
        print("Starting workers...")
        for i in range(50): # Spawn many workers to increase chance of race
            w_signals = WorkerSignals()
            # Direct connection which might be problematic under load/gc
            w_signals.log_message.connect(self.signals.log_message.emit)
            
            worker = Worker(w_signals)
            self.pool.start(worker)

    def on_log(self, msg):
        pass
        # print(f"Received: {msg}")

def main():
    app = QCoreApplication(sys.argv)
    
    manager = Manager()
    # Connect manager signal to a slot to complete the chain
    manager.signals.log_message.connect(manager.on_log)
    
    manager.start()
    
    # Run for a few seconds
    QThreadPool.globalInstance().waitForDone(2000)
    print("Done.")

if __name__ == "__main__":
    try:
        main()
    except AttributeError as e:
        print(f"\n!!! CRASH REPRODUCED !!!\n{e}")
    except Exception as e:
        print(f"An error occurred: {e}")
