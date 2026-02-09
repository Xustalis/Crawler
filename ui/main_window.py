"""
Refactored Main Window with language switcher and fixed category panel.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar,
    QGroupBox, QMessageBox, QFileDialog, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont

from core.scraped_data import ScrapedData
from workers.analyzer_worker import AnalyzerWorker
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
        self.analyzer: Optional[AnalyzerWorker] = None
        self.downloader: Optional[DownloaderWorker] = None
        self.scraped_data: Optional[ScrapedData] = None
        self.output_dir = './downloads'
        self.i18n = get_i18n()
        
        self._setup_ui()
        self._create_menu()
        self._check_environment()
    
    def _setup_ui(self) -> None:
        """Initialize UI."""
        self.setWindowTitle("Crawler - Web Resource Scraper")
        self.setMinimumSize(850, 650)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
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
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 20, 30, 20)
        
        # Header
        header = QLabel("🌐 Web Resource Crawler")
        header.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        header.setStyleSheet("color: #00a0ff;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Step 1: URL Input
        url_group = QGroupBox("第一步：输入网址")
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("例如: baidu.com (自动补全 https://)")
        self.url_input.returnPressed.connect(self._start_analysis)
        url_layout.addWidget(self.url_input, stretch=1)
        
        self.analyze_btn = QPushButton("🚀 开始分析")
        self.analyze_btn.clicked.connect(self._start_analysis)
        url_layout.addWidget(self.analyze_btn)
        
        url_group.setLayout(url_layout)
        main_layout.addWidget(url_group)
        
        # Step 2: Resource Selection (Fixed 3 categories)
        result_group = QGroupBox("第二步：选择资源类别")
        result_layout = QVBoxLayout()
        
        self.category_panel = CategoryPanel()
        self.category_panel.selection_changed.connect(self._update_download_state)
        result_layout.addWidget(self.category_panel)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.output_btn = QPushButton(f"📁 保存到: {self.output_dir}")
        self.output_btn.setStyleSheet("background-color: #444;")
        self.output_btn.clicked.connect(self._choose_directory)
        btn_layout.addWidget(self.output_btn)
        
        self.download_btn = QPushButton("⬇️ 下载选中资源")
        self.download_btn.setEnabled(False)
        self.download_btn.setStyleSheet("""
            QPushButton { background-color: #28a745; }
            QPushButton:hover { background-color: #34ce57; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self.download_btn, stretch=1)
        
        self.cancel_btn = QPushButton("⏹️ 取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #dc3545;")
        self.cancel_btn.clicked.connect(self._cancel_task)
        btn_layout.addWidget(self.cancel_btn)
        
        result_layout.addLayout(btn_layout)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group, stretch=1)
        
        # Progress
        progress_layout = QVBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #888;")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
        # Log
        self.log_widget = LogWidget()
        main_layout.addWidget(self.log_widget)
    
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
        lang_menu = menubar.addMenu("🌐 语言 / Language")
        
        zh_action = QAction("中文", self)
        zh_action.triggered.connect(lambda: self._change_language('zh'))
        lang_menu.addAction(zh_action)
        
        en_action = QAction("English", self)
        en_action.triggered.connect(lambda: self._change_language('en'))
        lang_menu.addAction(en_action)
    
    def _change_language(self, lang: str) -> None:
        """Change language."""
        self.i18n.set_language(lang)
        self._update_ui_texts()
        self.log_widget.append_log(f"✓ 语言已切换: {lang.upper()}")
    
    def _update_ui_texts(self) -> None:
        """Update UI texts for current language."""
        # Simplified - just update key labels
        is_zh = self.i18n.current_language == 'zh'
        self.analyze_btn.setText("🚀 开始分析" if is_zh else "🚀 Analyze")
        self.download_btn.setText("⬇️ 下载选中资源" if is_zh else "⬇️ Download")
        self.cancel_btn.setText("⏹️ 取消" if is_zh else "⏹️ Cancel")
    
    def _check_environment(self) -> None:
        """Check FFmpeg."""
        available, msg = check_ffmpeg()
        if available:
            self.log_widget.append_log(f"✓ FFmpeg: {msg}")
        else:
            self.log_widget.append_log(f"⚠ FFmpeg: {msg}")
    
    # --- Analysis ---
    
    def _start_analysis(self) -> None:
        """Start analyzing URL."""
        url = self.url_input.text().strip()
        if not url:
            return
        
        self.analyze_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.log_widget.clear_log()
        
        self.analyzer = AnalyzerWorker(url)
        self.analyzer.signals.log.connect(self.log_widget.append_log)
        self.analyzer.signals.progress.connect(self.status_label.setText)
        self.analyzer.signals.error.connect(self._on_analysis_error)
        self.analyzer.signals.finished.connect(self._on_analysis_done)
        self.analyzer.start()
    
    def _on_analysis_done(self, data: ScrapedData) -> None:
        """Handle analysis completion."""
        self.scraped_data = data
        self.analyze_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText("分析完成")
        
        self.category_panel.display_results(data)
        self._update_download_state()
        self.analyzer = None
    
    def _on_analysis_error(self, error: str) -> None:
        """Handle error."""
        self.analyze_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText("分析失败")
        self.log_widget.append_log(f"✗ {error}")
        
        # 友好的错误提示
        if "403" in error:
            QMessageBox.warning(self, "访问被拒绝", 
                "该网站拒绝了请求（403 Forbidden）。\n\n"
                "可能原因：\n"
                "• 网站有反爬虫保护\n"
                "• 需要登录才能访问\n"
                "• IP 被临时封禁")
        elif "timeout" in error.lower() or "超时" in error:
            QMessageBox.warning(self, "连接超时", "网络连接超时，请检查网络或稍后重试。")
        else:
            QMessageBox.warning(self, "分析失败", error)
        
        self.analyzer = None
    
    # --- Download ---
    
    def _start_download(self) -> None:
        """Start batch download."""
        if not self.scraped_data:
            return
        
        selected = self.category_panel.get_selected_categories()
        if not selected:
            return
        
        self.download_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.category_panel.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.downloader = DownloaderWorker(
            self.scraped_data, selected, self.output_dir
        )
        self.downloader.signals.log.connect(self.log_widget.append_log)
        self.downloader.signals.overall_progress.connect(self._on_progress)
        self.downloader.signals.finished.connect(self._on_download_done)
        self.downloader.start()
    
    def _on_progress(self, current: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
            self.status_label.setText(f"下载中: {current}/{total}")
    
    def _on_download_done(self, success: int, total: int) -> None:
        """Handle download completion."""
        self.download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.category_panel.setEnabled(True)
        self.status_label.setText("完成")
        
        if success > 0:
            QMessageBox.information(
                self, "下载完成",
                f"成功: {success}/{total}\n\n保存到: {self.output_dir}"
            )
        self.downloader = None
    
    def _cancel_task(self) -> None:
        """Cancel current task."""
        if self.analyzer:
            self.analyzer.cancel()
        if self.downloader:
            self.downloader.cancel()
        self.cancel_btn.setEnabled(False)
        self.log_widget.append_log("⏹ 已取消")
    
    def _choose_directory(self) -> None:
        """Select output directory."""
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.output_dir)
        if path:
            self.output_dir = path
            self.output_btn.setText(f"📁 保存到: {path}")
    
    def _update_download_state(self) -> None:
        """Update download button state."""
        self.download_btn.setEnabled(self.category_panel.has_selection())
    
    def closeEvent(self, event) -> None:
        """Cleanup on close - properly stop threads to prevent crash."""
        # 先取消任务
        if self.analyzer:
            self.analyzer.cancel()
        if self.downloader:
            self.downloader.cancel()
        
        # 等待线程结束
        if self.analyzer and self.analyzer.isRunning():
            self.analyzer.quit()
            self.analyzer.wait(2000)  # 最多等2秒
            
        if self.downloader and self.downloader.isRunning():
            self.downloader.quit()
            self.downloader.wait(2000)
        
        event.accept()
