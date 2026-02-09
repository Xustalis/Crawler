"""
Refactored Main Window with language switcher and fixed category panel.
"""

from typing import Optional, List
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar,
    QGroupBox, QMessageBox, QFileDialog, QMenuBar, QMenu,
    QSlider, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont

from core.scraped_data import ScrapedData, ResourceCategory
from workers.worker_pool import WorkerPool
from workers.downloader_worker import DownloaderWorker
from ui.widgets import CategoryPanel, LogWidget
from ui.i18n import get_i18n, t
from utils.ffmpeg_checker import check_ffmpeg
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window with language switcher."""
    
    def __init__(self):
        super().__init__()
        self.worker_pool: Optional[WorkerPool] = None
        self.downloader: Optional[DownloaderWorker] = None
        self.scraped_data: Optional[ScrapedData] = None
        self.output_dir = os.path.abspath('./downloads')
        self.i18n = get_i18n()
        
        # Intelligent default concurrency
        cpu_count = os.cpu_count() or 4
        self.num_workers = min(10, max(5, cpu_count * 2))
        
        self._setup_ui()
        self._create_menu()
        self._check_environment()
        
        # Initial translation
        self.retranslateUi()
    
    def _setup_ui(self) -> None:
        """Initialize UI with Tabs."""
        self.setWindowTitle("Crawler V2.0")
        self.setMinimumSize(900, 750)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background: #1e1e1e;
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #888;
                padding: 10px 20px;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                color: #00a0ff;
                border-bottom: 2px solid #00a0ff;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #00a0ff;
            }
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #00a0ff;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
            QProgressBar {
                background-color: #2a2a2a;
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #00a0ff;
                border-radius: 4px;
            }
        """)
        
        # Tabs
        from PyQt6.QtWidgets import QTabWidget
        from ui.history_widget import HistoryWidget
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # --- Tab 1: New Task ---
        self.tab_new = QWidget()
        self.tabs.addTab(self.tab_new, "New Task")
        
        main_layout = QVBoxLayout(self.tab_new)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.header_label = QLabel()
        self.header_label.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.Bold))
        self.header_label.setStyleSheet("color: #00a0ff;")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.header_label)
        
        # Step 1: URL Input
        self.url_group = QGroupBox()
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self._start_analysis)
        url_layout.addWidget(self.url_input, stretch=1)
        
        self.analyze_btn = QPushButton()
        self.analyze_btn.clicked.connect(self._start_analysis)
        url_layout.addWidget(self.analyze_btn)
        
        self.url_group.setLayout(url_layout)
        main_layout.addWidget(self.url_group)
        
        # Step 1.5: Concurrency
        self.concurrency_group = QGroupBox()
        concurrency_layout = QHBoxLayout()
        
        self.concurrency_label = QLabel(f"Workers: {self.num_workers}")
        self.concurrency_label.setStyleSheet("font-size: 12px;") 
        concurrency_layout.addWidget(self.concurrency_label)
        
        self.concurrency_slider = QSlider(Qt.Orientation.Horizontal)
        self.concurrency_slider.setMinimum(1)
        self.concurrency_slider.setMaximum(20)
        self.concurrency_slider.setValue(self.num_workers)
        self.concurrency_slider.setTickInterval(1)
        self.concurrency_slider.valueChanged.connect(self._on_concurrency_changed)
        concurrency_layout.addWidget(self.concurrency_slider)
        
        self.concurrency_group.setLayout(concurrency_layout)
        main_layout.addWidget(self.concurrency_group)
        
        # Step 2: Resource Selection
        self.result_group = QGroupBox()
        result_layout = QVBoxLayout()
        
        self.category_panel = CategoryPanel()
        self.category_panel.selection_changed.connect(self._update_download_state)
        
        scroll = QScrollArea()
        scroll.setWidget(self.category_panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumHeight(60)  
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        result_layout.addWidget(scroll)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.output_btn = QPushButton()
        self.output_btn.setStyleSheet("background-color: #444;")
        self.output_btn.clicked.connect(self._choose_directory)
        btn_layout.addWidget(self.output_btn)
        
        self.download_btn = QPushButton()
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet("""
            QPushButton { background-color: #28a745; }
            QPushButton:hover { background-color: #34ce57; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self.download_btn, stretch=1)
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #dc3545;")
        self.cancel_btn.clicked.connect(self._cancel_task)
        btn_layout.addWidget(self.cancel_btn)
        
        result_layout.addLayout(btn_layout)
        self.result_group.setLayout(result_layout)
        main_layout.addWidget(self.result_group)
        
        # Progress
        progress_layout = QVBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888;")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # Log
        self.log_group = QGroupBox()
        log_layout = QVBoxLayout()
        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)
        self.log_group.setLayout(log_layout)
        main_layout.addWidget(self.log_group)
        
        # --- Tab 2: History ---
        self.tab_history = HistoryWidget()
        self.tabs.addTab(self.tab_history, "History")
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        if index == 1: # History tab
            self.tab_history.load_history()
    
    def _create_menu(self) -> None:
        """Create menu bar with language switcher."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2a2a2a;
                color: #ffffff;
                padding: 5px;
            }
            QMenuBar::item:selected {
                background-color: #444;
            }
            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background-color: #007acc;
            }
        """)
        
        # Language menu
        self.lang_menu = menubar.addMenu("Language") # Will update in retranslateUi
        
        zh_action = QAction("中文", self)
        zh_action.triggered.connect(lambda: self._change_language('zh'))
        self.lang_menu.addAction(zh_action)
        
        en_action = QAction("English", self)
        en_action.triggered.connect(lambda: self._change_language('en'))
        self.lang_menu.addAction(en_action)
    
    def retranslateUi(self):
        """Update all UI texts based on current language."""
        self.setWindowTitle(t('app_title'))
        self.header_label.setText(t('header_title'))
        
        self.url_group.setTitle(t('url_section_title'))
        self.url_input.setPlaceholderText(t('url_placeholder'))
        self.analyze_btn.setText(t('analyze_button'))
        
        # Concurrency group title
        self.concurrency_group.setTitle(t('concurrency_title'))
        self.concurrency_label.setText(t('concurrency_label', self.num_workers))
        
        self.result_group.setTitle(t('resources_title')) # Or download_section_title? resources_title fits better for the panel area
        
        self._update_output_btn_text()
        self.download_btn.setText(t('download_button'))
        self.cancel_btn.setText(t('cancel_button'))
        
        self.status_label.setText(t('status_ready'))
        self.lang_menu.setTitle(t('menu_language'))
        
        self.log_group.setTitle(t('log_title'))
        
        # Update children
        self.category_panel.update_texts()

    def _change_language(self, lang: str) -> None:
        """Change language."""
        self.i18n.set_language(lang)
        self.retranslateUi()
        self.log_widget.append_log(f"✓ Language changed: {lang.upper()}")
    
    def _update_output_btn_text(self):
        # We format the directory path into the button text
        # But we need the prefix Translated.
        # "📁 Save to: ..."
        # i18n key 'log_output_dir' is "Output directory: {0}". 
        # I'll use a new format or reuse. 
        # reusing 'choose_dir_button' might be weird if it just says "Choose Dir".
        # Let's check i18n keys. 'choose_dir_button': 'Choose Output Dir'.
        # I will construct it manually for now to include path.
        prefix = "📁 保存到: " if self.i18n.current_language == 'zh' else "📁 Save to: "
        self.output_btn.setText(f"{prefix}{self.output_dir}")

    def _on_concurrency_changed(self, val):
        self.num_workers = val
        self.concurrency_label.setText(t('concurrency_label', val))

    def _check_environment(self) -> None:
        """Check FFmpeg."""
        available, msg = check_ffmpeg()
        if available:
            self.log_widget.append_log(t('log_ffmpeg_detected', msg))
        else:
            self.log_widget.append_log(t('log_ffmpeg_warning', msg))
            self.log_widget.append_log(t('log_ffmpeg_required'))

    def _start_analysis(self) -> None:
        """Start analyzing URL with worker pool."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, t('dialog_input_error'), t('dialog_enter_url'))
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        self._set_encoding_state(True)
        self.log_widget.clear_log()
        self.log_widget.append_log(t('log_analyzing_url', url))
        
        self.worker_pool = WorkerPool(num_workers=self.num_workers, max_depth=2)
        self.worker_pool.log_message.connect(self.log_widget.append_log)
        self.worker_pool.pool_progress.connect(self._on_pool_progress)
        self.worker_pool.pool_finished.connect(self._on_analysis_done)
        self.worker_pool.error_occurred.connect(self._on_analysis_error)
        
        self.worker_pool.start_crawl(url)
        self.status_label.setText(t('status_analyzing'))
    
    def _set_encoding_state(self, is_running: bool):
        """Disable/Enable UI during tasks."""
        self.analyze_btn.setEnabled(not is_running)
        self.url_input.setEnabled(not is_running)
        self.download_btn.setEnabled(not is_running)
        self.concurrency_slider.setEnabled(not is_running)
        self.cancel_btn.setEnabled(is_running)
        if is_running:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

    def _on_pool_progress(self, completed: int, total: int):
        if total > 0:
            self.progress_bar.setRange(0, 100)
            progress = int((completed / total) * 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(t('progress_status', completed, total))
    
    def _on_analysis_done(self, data: ScrapedData) -> None:
        self.scraped_data = data
        self._set_encoding_state(False)
        self.progress_bar.setValue(100)
        self.status_label.setText(t('progress_complete'))
        
        summary = data.summary() if self.i18n.current_language == 'zh' else data.summary_en()
        self.log_widget.append_log(f"✓ {summary}")
        
        self.category_panel.display_results(data)
        self._update_download_state()
        self.worker_pool = None
    
    def _on_analysis_error(self, error: str) -> None:
        self._set_encoding_state(False)
        self.status_label.setText(t('status_error'))
        self.log_widget.append_log(f"✗ {error}")
        QMessageBox.warning(self, t('dialog_error'), error)
        self.worker_pool = None

    def _start_download(self) -> None:
        """Start batch download with filtered selection."""
        if not self.scraped_data:
            return
        
        # Get Selection
        selection_map = self.category_panel.get_selected_map()
        
        # Filter ScrapedData
        filtered_data = ScrapedData()
        filtered_data.source_url = self.scraped_data.source_url
        
        # Helper to filter list by URL set
        def filter_group(original_list, key):
             selected_set = selection_map.get(key, set())
             return [r for r in original_list if r.url in selected_set]
        
        filtered_data.images = filter_group(self.scraped_data.images, 'images')
        
        # Group 'videos' in UI -> videos + m3u8 in data
        filtered_data.videos = filter_group(self.scraped_data.videos, 'videos')
        filtered_data.m3u8_streams = filter_group(self.scraped_data.m3u8_streams, 'videos')
        
        # Group 'documents' in UI -> documents + audios in data
        filtered_data.documents = filter_group(self.scraped_data.documents, 'documents')
        filtered_data.audios = filter_group(self.scraped_data.audios, 'documents')
        
        # Determine categories to download
        categories = []
        count = 0
        if filtered_data.images: 
            categories.append(ResourceCategory.IMAGES)
            count += len(filtered_data.images)
        if filtered_data.videos: 
            categories.append(ResourceCategory.VIDEOS)
            count += len(filtered_data.videos)
        if filtered_data.m3u8_streams: 
            categories.append(ResourceCategory.M3U8_STREAMS)
            count += len(filtered_data.m3u8_streams)
        if filtered_data.documents: 
            categories.append(ResourceCategory.DOCUMENTS)
            count += len(filtered_data.documents)
        if filtered_data.audios: 
            categories.append(ResourceCategory.AUDIOS)
            count += len(filtered_data.audios)
            
        if count == 0:
            QMessageBox.warning(self, t('dialog_selection_error'), t('dialog_select_resources'))
            return
            
        # Update UI state
        self.download_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.category_panel.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.log_widget.append_log(t('log_starting_download', count))
        
        self.downloader = DownloaderWorker(
            filtered_data, categories, self.output_dir
        )
        self.downloader.signals.log.connect(self.log_widget.append_log)
        self.downloader.signals.overall_progress.connect(self._on_progress)
        self.downloader.signals.finished.connect(self._on_download_done)
        self.downloader.start()
    
    def _on_progress(self, current: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
            self.status_label.setText(t('progress_status', current, total))
    
    def _on_download_done(self, success: int, total: int) -> None:
        self.download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.category_panel.setEnabled(True)
        self.status_label.setText(t('progress_all_done'))
        
        if success > 0:
            QMessageBox.information(
                self, t('dialog_success'),
                t('dialog_downloads_complete', self.output_dir)
            )
        self.downloader = None
    
    def _choose_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(self, t('dialog_select_output_dir'), self.output_dir)
        if path:
            self.output_dir = path
            self._update_output_btn_text()
    
    def _update_download_state(self) -> None:
        self.download_btn.setEnabled(self.category_panel.has_selection())

    def _cancel_task(self) -> None:
        if self.worker_pool:
            self.worker_pool.cancel()
        if self.downloader:
            self.downloader.cancel()
        self.cancel_btn.setEnabled(False)
        self.log_widget.append_log(t('log_cancelling'))
        
    def closeEvent(self, event) -> None:
        if self.worker_pool:
            self.worker_pool.cancel()
        if self.downloader:
            self.downloader.cancel()
        if self.downloader and self.downloader.isRunning():
            self.downloader.quit()
            self.downloader.wait(2000)
        event.accept()
