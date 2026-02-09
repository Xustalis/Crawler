"""
Main window for the Crawler application.

Implements the primary UI with proper MVC separation and signal-slot connections.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar,
    QGroupBox, QMessageBox, QFileDialog, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from core.models import Resource
from workers.crawler_worker import CrawlerWorker
from ui.widgets import ResourceListWidget, LogWidget
from ui.i18n import get_i18n, t
from utils.ffmpeg_checker import check_ffmpeg
from utils.logger import setup_logger


logger = setup_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Responsibilities:
    - Manage UI layout
    - Connect signals from worker threads
    - Handle user interactions
    - Display progress and logs
    
    CRITICAL: All worker signals must be connected in the UI thread!
    """
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.output_dir = './downloads'
        self.i18n = get_i18n()
        self._setup_ui()
        self._create_menu()
        self._check_environment()
    
    def _setup_ui(self) -> None:
        """Initialize UI components and layout."""
        self.setWindowTitle(t('app_title'))
        self.setMinimumSize(900, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.header = QLabel(t('header_title'))
        self.header.setStyleSheet("font-size: 20px; font-weight: bold; color: #00a0ff;")
        main_layout.addWidget(self.header)
        
        # URL input section
        url_group = self._create_url_section()
        main_layout.addWidget(url_group)
        
        # Resource list
        self.resource_list = ResourceListWidget()
        main_layout.addWidget(self.resource_list, stretch=2)
        
        # Download controls
        download_group = self._create_download_section()
        main_layout.addWidget(download_group)
        
        # Progress section
        progress_group = self._create_progress_section()
        main_layout.addWidget(progress_group)
        
        # Log widget
        self.log_label = QLabel(t('log_title'))
        self.log_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.log_label)
        
        self.log_widget = LogWidget()
        main_layout.addWidget(self.log_widget)
        
        # Status bar
        self.statusBar().showMessage(t('status_ready'))
    
    def _create_url_section(self) -> QGroupBox:
        """Create URL input section."""
        self.url_group = QGroupBox(t('url_section_title'))
        layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(t('url_placeholder'))
        self.url_input.returnPressed.connect(self._on_analyze_clicked)
        layout.addWidget(self.url_input, stretch=1)
        
        self.analyze_btn = QPushButton(t('analyze_button'))
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self.analyze_btn)
        
        self.url_group.setLayout(layout)
        return self.url_group
    
    def _create_download_section(self) -> QGroupBox:
        """Create download controls section."""
        self.download_group = QGroupBox(t('download_section_title'))
        layout = QHBoxLayout()
        
        self.download_btn = QPushButton(t('download_button'))
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download_clicked)
        layout.addWidget(self.download_btn)
        
        self.pause_btn = QPushButton(t('pause_button'))
        self.pause_btn.setObjectName("secondaryButton")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton(t('cancel_button'))
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self.cancel_btn)
        
        self.choose_dir_btn = QPushButton(t('choose_dir_button'))
        self.choose_dir_btn.setObjectName("secondaryButton")
        self.choose_dir_btn.clicked.connect(self._on_choose_directory)
        layout.addWidget(self.choose_dir_btn)
        
        layout.addStretch()
        
        self.download_group.setLayout(layout)
        return self.download_group
    
    def _create_progress_section(self) -> QGroupBox:
        """Create progress display section."""
        self.progress_group = QGroupBox(t('progress_title'))
        layout = QVBoxLayout()
        
        # Overall progress
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel(t('progress_ready'))
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar, stretch=1)
        
        layout.addLayout(progress_layout)
        
        self.progress_group.setLayout(layout)
        return self.progress_group
    
    def _create_menu(self) -> None:
        """Create menu bar with language switcher."""
        menubar = self.menuBar()
        
        # Language menu
        lang_menu = menubar.addMenu(t('menu_language'))
        
        # Chinese action
        zh_action = QAction('中文', self)
        zh_action.triggered.connect(lambda: self._change_language('zh'))
        lang_menu.addAction(zh_action)
        
        # English action
        en_action = QAction('English', self)
        en_action.triggered.connect(lambda: self._change_language('en'))
        lang_menu.addAction(en_action)
    
    def _change_language(self, lang: str) -> None:
        """Change application language."""
        self.i18n.set_language(lang)
        self._update_ui_texts()
        logger.info(f"Language changed to: {lang}")
    
    def _update_ui_texts(self) -> None:
        """Update all UI texts with current language."""
        # Window title
        self.setWindowTitle(t('app_title'))
        
        # Header
        self.header.setText(t('header_title'))
        
        # URL section
        self.url_group.setTitle(t('url_section_title'))
        self.url_input.setPlaceholderText(t('url_placeholder'))
        self.analyze_btn.setText(t('analyze_button'))
        
        # Download section
        self.download_group.setTitle(t('download_section_title'))
        self.download_btn.setText(t('download_button'))
        current_pause_text = self.pause_btn.text()
        if '▶️' in current_pause_text:
            self.pause_btn.setText(t('resume_button'))
        else:
            self.pause_btn.setText(t('pause_button'))
        self.cancel_btn.setText(t('cancel_button'))
        self.choose_dir_btn.setText(t('choose_dir_button'))
        
        # Progress section
        self.progress_group.setTitle(t('progress_title'))
        
        # Log section
        self.log_label.setText(t('log_title'))
        
        # Update resource list
        self.resource_list.update_language()
    
    def _check_environment(self) -> None:
        """Check FFmpeg availability on startup."""
        available, message = check_ffmpeg()
        
        if available:
            self.log_widget.append_log(t('log_ffmpeg_detected', message))
        else:
            self.log_widget.append_log(t('log_ffmpeg_warning', message))
            self.log_widget.append_log(t('log_ffmpeg_required'))
    
    # Button handlers
    
    def _on_analyze_clicked(self) -> None:
        """Handle Analyze button click."""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, t('dialog_input_error'), t('dialog_enter_url'))
            return
        
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, t('dialog_input_error'), t('dialog_invalid_url'))
            return
        
        self._start_analysis(url)
    
    def _on_download_clicked(self) -> None:
        """Handle Download button click."""
        selected = self.resource_list.get_selected_resources()
        
        if not selected:
            QMessageBox.warning(self, t('dialog_selection_error'), t('dialog_select_resources'))
            return
        
        self._start_download(selected)
    
    def _on_pause_clicked(self) -> None:
        """Handle Pause/Resume button click."""
        if self.worker and self.worker.is_running_task():
            if t('pause_button') in self.pause_btn.text() or '⏸' in self.pause_btn.text():
                self.worker.pause()
                self.pause_btn.setText(t('resume_button'))
            else:
                self.worker.resume()
                self.pause_btn.setText(t('pause_button'))
    
    def _on_cancel_clicked(self) -> None:
        """Handle Cancel button click."""
        if self.worker:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
    
    def _on_choose_directory(self) -> None:
        """Handle directory selection."""
        directory = QFileDialog.getExistingDirectory(
            self,
            t('dialog_select_output_dir'),
            self.output_dir
        )
        
        if directory:
            self.output_dir = directory
            self.log_widget.append_log(t('log_output_dir', directory))
    
    # Worker management
    
    def _start_analysis(self, url: str) -> None:
        """Start URL analysis worker."""
        # Clean up previous worker
        if self.worker:
            self.worker.quit()
            self.worker.wait()
        
        # Create new worker
        self.worker = CrawlerWorker(url=url, output_dir=self.output_dir)
        self._connect_signals()
        
        # Update UI state
        self.analyze_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.resource_list.set_resources([])
        
        # Start worker
        self.worker.start()
        logger.info(f"Started analysis worker for: {url}")
    
    def _start_download(self, resources: list) -> None:
        """Start download worker."""
        # Clean up previous worker
        if self.worker:
            self.worker.quit()
            self.worker.wait()
        
        # Create new worker
        self.worker = CrawlerWorker(
            url="",
            resources_to_download=resources,
            output_dir=self.output_dir
        )
        self._connect_signals()
        
        # Update UI state
        self.download_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Start worker
        self.worker.start()
        logger.info(f"Started download worker for {len(resources)} resources")
    
    def _connect_signals(self) -> None:
        """Connect worker signals to UI slots."""
        if not self.worker:
            return
        
        signals = self.worker.signals
        
        # Analysis signals
        signals.analysis_started.connect(self._on_analysis_started)
        signals.resources_found.connect(self._on_resources_found)
        signals.analysis_completed.connect(self._on_analysis_completed)
        
        # Download signals
        signals.download_started.connect(self._on_download_started)
        signals.download_progress.connect(self._on_download_progress)
        signals.download_completed.connect(self._on_download_completed)
        signals.download_failed.connect(self._on_download_failed)
        
        # Overall progress
        signals.overall_progress.connect(self._on_overall_progress)
        
        # Logging
        signals.log_message.connect(self.log_widget.append_log)
        
        # Errors
        signals.error_occurred.connect(self._on_error)
        
        # Completion
        signals.task_finished.connect(self._on_task_finished)
    
    # Signal handlers (slots)
    
    def _on_analysis_started(self) -> None:
        """Handle analysis start."""
        self.progress_label.setText(t('progress_analyzing'))
        self.statusBar().showMessage(t('status_analyzing'))
    
    def _on_resources_found(self, resources: list) -> None:
        """Handle resources discovery."""
        self.resource_list.set_resources(resources)
        self.download_btn.setEnabled(len(resources) > 0)
    
    def _on_analysis_completed(self) -> None:
        """Handle analysis completion."""
        self.analyze_btn.setEnabled(True)
        self.progress_label.setText(t('progress_complete'))
        self.statusBar().showMessage(t('status_ready'))
    
    def _on_download_started(self, resource: Resource) -> None:
        """Handle download start."""
        self.progress_label.setText(t('progress_downloading', resource.title[:50] + '...'))
    
    def _on_download_progress(self, resource: Resource, progress: float) -> None:
        """Handle download progress update."""
        self.resource_list.update_resource_progress(resource, progress)
        self.progress_bar.setValue(int(progress * 100))
    
    def _on_download_completed(self, resource: Resource) -> None:
        """Handle download completion."""
        self.resource_list.update_resource_progress(resource, 1.0)
    
    def _on_download_failed(self, resource: Resource, error: str) -> None:
        """Handle download failure."""
        logger.error(f"Download failed: {resource.title} - {error}")
    
    def _on_overall_progress(self, completed: int, total: int) -> None:
        """Handle overall progress update."""
        self.progress_label.setText(t('progress_status', completed, total))
        if total > 0:
            self.progress_bar.setValue(int((completed / total) * 100))
    
    def _on_error(self, error_message: str) -> None:
        """Handle error."""
        QMessageBox.critical(self, t('dialog_error'), error_message)
        self.statusBar().showMessage(t('status_error'))
    
    def _on_task_finished(self) -> None:
        """Handle task completion."""
        self.analyze_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_label.setText(t('progress_all_done'))
        self.statusBar().showMessage(t('status_ready'))
        
        QMessageBox.information(
            self,
            t('dialog_success'),
            t('dialog_downloads_complete', self.output_dir)
        )
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Clean up worker thread
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait(3000)  # Wait up to 3 seconds
        
        event.accept()
