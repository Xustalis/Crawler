
import unittest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication
from core.signals import PoolSignals, WorkerSignals

class TestSignals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a QApp instance if it doesn't exist
        if not QCoreApplication.instance():
            cls.app = QCoreApplication(sys.argv)
        else:
            cls.app = QCoreApplication.instance()

    def test_pool_signals_definitions(self):
        signals = PoolSignals()
        self.assertTrue(hasattr(signals, 'log_message'))
        self.assertTrue(hasattr(signals, 'started'))
        self.assertTrue(hasattr(signals, 'finished'))
        self.assertTrue(hasattr(signals, 'error'))
        self.assertTrue(hasattr(signals, 'progress'))
        self.assertTrue(hasattr(signals, 'results_updated'))

    def test_worker_signals_definitions(self):
        signals = WorkerSignals()
        self.assertTrue(hasattr(signals, 'log_message'))
        self.assertTrue(hasattr(signals, 'task_started'))
        self.assertTrue(hasattr(signals, 'task_completed'))
        self.assertTrue(hasattr(signals, 'task_failed'))

    def test_emit_log_message(self):
        signals = PoolSignals()
        received = []
        
        def on_log(msg):
            received.append(msg)
            
        signals.log_message.connect(on_log)
        signals.log_message.emit("Test message")
        
        self.assertEqual(received, ["Test message"])

if __name__ == '__main__':
    unittest.main()
