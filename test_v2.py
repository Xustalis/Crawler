import sys
import unittest
from unittest.mock import patch

sys.path.append(".")

from PyQt6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])

from core.database import DatabaseManager
from core.models import Resource, ResourceType
from core.scraped_data import ScrapedData, ResourceCategory
from ui.main_window import MainWindow
import ui.main_window as main_window_mod
from workers.downloader_worker import DownloadRunnable

class _DummySignal:
    def __init__(self):
        self.connected = []

    def connect(self, fn):
        self.connected.append(fn)


class _DummyDownloaderSignals:
    def __init__(self):
        self.log = _DummySignal()
        self.file_log = _DummySignal()
        self.progress = _DummySignal()
        self.error = _DummySignal()
        self.finished = _DummySignal()


class _DummyDownloaderWorker:
    def __init__(self, scraped_data, selected_categories, output_dir, max_workers=5):
        self.scraped_data = scraped_data
        self.selected_categories = selected_categories
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.signals = _DummyDownloaderSignals()
        self.started = False

    def start(self):
        self.started = True

    def cancel(self):
        pass

    def isRunning(self):
        return False


class TestModelsAndDownload(unittest.TestCase):
    def test_resource_type_inference(self):
        r = Resource(url="https://example.com/a.jpg")
        self.assertEqual(r.resource_type, ResourceType.IMAGE)

    def test_download_runnable_guess_extension_fallback(self):
        db = DatabaseManager(":memory:")
        headers = {}

        r_img = Resource(url="https://example.com/noext", resource_type=ResourceType.IMAGE)
        rr_img = DownloadRunnable(r_img, "out", 1, db, headers)
        self.assertEqual(rr_img._guess_extension(r_img.url), ".jpg")

        r_vid = Resource(url="https://example.com/noext", resource_type=ResourceType.VIDEO)
        rr_vid = DownloadRunnable(r_vid, "out", 1, db, headers)
        self.assertEqual(rr_vid._guess_extension(r_vid.url), ".mp4")

        r_m3u8 = Resource(url="https://example.com/noext", resource_type=ResourceType.M3U8)
        rr_m3u8 = DownloadRunnable(r_m3u8, "out", 1, db, headers)
        self.assertEqual(rr_m3u8._guess_extension(r_m3u8.url), ".mp4")


class TestMainWindowDownloadWiring(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_start_download_uses_progress_signal(self):
        data = ScrapedData(source_url="https://example.com")
        img = Resource(url="https://example.com/a.jpg", resource_type=ResourceType.IMAGE)
        data.images = [img]
        self.window.scraped_data = data
        self.window.category_panel.display_results(data)
        self.window.category_panel.selected_resources["images"] = {img.url}

        with patch.object(main_window_mod, "DownloaderWorker", _DummyDownloaderWorker):
            self.window._start_download()
            self.assertIsInstance(self.window.downloader, _DummyDownloaderWorker)
            self.assertTrue(self.window.downloader.signals.progress.connected)
            self.assertTrue(self.window.downloader.started)


if __name__ == "__main__":
    unittest.main()
