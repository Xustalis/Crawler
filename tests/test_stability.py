import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.url_normalizer import validate_url, is_valid_url, normalize_url
from core.downloader import Downloader
from core.models import Resource, ResourceType
from workers.downloader_worker import DownloadRunnable

class TestUrlNormalizer(unittest.TestCase):
    def test_valid_urls(self):
        valid_urls = [
            "https://google.com",
            "http://example.com/path",
            "https://sub.domain.co.uk:8080/resource?query=1",
            "ftp://ftp.server.com"
        ]
        for url in valid_urls:
            self.assertTrue(is_valid_url(url), f"Should be valid: {url}")

    def test_invalid_urls(self):
        invalid_urls = [
            "not_a_url",
            "http://",
            "://missing.scheme",
            "just text",
            "",
            None
        ]
        for url in invalid_urls:
            self.assertFalse(is_valid_url(url), f"Should be invalid: {url}")

    def test_normalization(self):
        self.assertEqual(normalize_url("google.com"), "https://google.com")
        self.assertEqual(normalize_url("  http://test.com  "), "http://test.com")

    def test_validation_raises(self):
        with self.assertRaises(ValueError):
            validate_url("invalid_url_string")

class TestDownloaderStability(unittest.TestCase):
    def setUp(self):
        self.downloader = Downloader(output_dir="./test_downloads")
        self.resource = Resource(url="https://example.com/file.txt", title="Test File")

    def tearDown(self):
        if Path("./test_downloads").exists():
            import shutil
            shutil.rmtree("./test_downloads")

    @patch('core.downloader.requests.get')
    def test_download_disk_space_check(self, mock_get):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content.return_value = [b'content']
        mock_get.return_value = mock_response

        # Mock disk usage to return low space
        with patch('shutil.disk_usage') as mock_usage:
            # total, used, free
            mock_usage.return_value = (1000, 500, 100) # Only 100 bytes free
            
            # Should fail due to disk space
            result = self.downloader.download(self.resource)
            self.assertFalse(result)
            self.assertIn("Insufficient disk space", self.resource.error_message or "")

    @patch('core.downloader.requests.get')
    def test_download_success(self, mock_get):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '10'}
        mock_response.iter_content.return_value = [b'1234567890']
        mock_get.return_value = mock_response

        with patch('shutil.disk_usage') as mock_usage:
            # Plenty of space
            mock_usage.return_value = (10**9, 0, 10**9)
            
            result = self.downloader.download(self.resource)
            self.assertTrue(result)
            self.assertEqual(self.resource.status.value, "completed")
            self.assertTrue(Path(self.resource.local_path).exists())

class TestWorkerPoolSignals(unittest.TestCase):
    def test_pool_instantiation(self):
        from workers.worker_pool import WorkerPool
        from PyQt6.QtCore import QCoreApplication
        
        # QObject needs a QApp
        if not QCoreApplication.instance():
            self.app = QCoreApplication([])
            
        
        pool = WorkerPool(num_workers=1, max_depth=1)
        # Check if signal exists
        self.assertTrue(hasattr(pool.signals, 'log_message'))
        
        # Test emission
        mock_slot = MagicMock()
        pool.signals.log_message.connect(mock_slot)
        pool.signals.log_message.emit("Test")
        mock_slot.assert_called_with("Test")

if __name__ == '__main__':
    unittest.main()
