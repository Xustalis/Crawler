"""
Refactored UI widgets with fixed category design.
Uses QLabel for text visibility instead of QCheckBox text.
"""

from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
    QLabel, QProgressBar, QTextEdit, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor, QFont

from core.scraped_data import ScrapedData, ResourceCategory


class CategoryCheckbox(QFrame):
    """
    Single category checkbox with visible label.
    Uses QLabel for guaranteed text visibility.
    """
    
    stateChanged = pyqtSignal(bool)
    
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 5px;
            }
            QFrame:hover {
                border-color: #00a0ff;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(12)
        
        # Checkbox (no text)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #00a0ff;
                background: #1e1e1e;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #00a0ff;
                background: #00a0ff;
                border-radius: 4px;
            }
        """)
        self.checkbox.stateChanged.connect(lambda: self.stateChanged.emit(self.checkbox.isChecked()))
        layout.addWidget(self.checkbox)
        
        # Icon label
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 18))
        layout.addWidget(icon_label)
        
        # Text label
        self.text_label = QLabel(label)
        self.text_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.text_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.text_label)
        
        # Count label
        self.count_label = QLabel("(0)")
        self.count_label.setFont(QFont("Microsoft YaHei", 12))
        self.count_label.setStyleSheet("color: #888;")
        layout.addWidget(self.count_label)
        
        layout.addStretch()
    
    def set_count(self, count: int) -> None:
        """Update the count display."""
        self.count_label.setText(f"({count} 个)")
        if count > 0:
            self.setEnabled(True)
            self.count_label.setStyleSheet("color: #4ec9b0;")
        else:
            self.setEnabled(False)
            self.checkbox.setChecked(False)
            self.count_label.setStyleSheet("color: #666;")
            self.text_label.setStyleSheet("color: #666;")
    
    def is_checked(self) -> bool:
        return self.checkbox.isChecked()
    
    def set_checked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)


class CategoryPanel(QWidget):
    """
    Panel showing 3 fixed categories: Image, Video, Text/Documents.
    """
    
    selection_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scraped_data: Optional[ScrapedData] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 固定的三个类别
        self.image_cb = CategoryCheckbox("🖼️", "图片资源")
        self.image_cb.stateChanged.connect(self._on_changed)
        layout.addWidget(self.image_cb)
        
        self.video_cb = CategoryCheckbox("🎬", "视频资源")
        self.video_cb.stateChanged.connect(self._on_changed)
        layout.addWidget(self.video_cb)
        
        self.text_cb = CategoryCheckbox("📄", "文档资源")
        self.text_cb.stateChanged.connect(self._on_changed)
        layout.addWidget(self.text_cb)
        
        layout.addStretch()
    
    def display_results(self, data: ScrapedData) -> None:
        """Update counts from scraped data."""
        self.scraped_data = data
        
        # 图片 = images
        img_count = len(data.images)
        self.image_cb.set_count(img_count)
        if img_count > 0:
            self.image_cb.set_checked(True)
        
        # 视频 = videos + m3u8_streams
        video_count = len(data.videos) + len(data.m3u8_streams)
        self.video_cb.set_count(video_count)
        if video_count > 0:
            self.video_cb.set_checked(True)
        
        # 文档 = documents + audios
        doc_count = len(data.documents) + len(data.audios)
        self.text_cb.set_count(doc_count)
    
    def get_selected_categories(self) -> List[ResourceCategory]:
        """Return selected categories."""
        selected = []
        if self.image_cb.is_checked():
            selected.append(ResourceCategory.IMAGES)
        if self.video_cb.is_checked():
            selected.append(ResourceCategory.VIDEOS)
            selected.append(ResourceCategory.M3U8_STREAMS)
        if self.text_cb.is_checked():
            selected.append(ResourceCategory.DOCUMENTS)
            selected.append(ResourceCategory.AUDIOS)
        return selected
    
    def _on_changed(self) -> None:
        self.selection_changed.emit()
    
    def has_selection(self) -> bool:
        return (self.image_cb.is_checked() or 
                self.video_cb.is_checked() or 
                self.text_cb.is_checked())


class LogWidget(QTextEdit):
    """Log display widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(150)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #cccccc;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
    def append_log(self, message: str) -> None:
        """Append colored log message."""
        if "✓" in message or "成功" in message:
            color = "#4ec9b0"
        elif "✗" in message or "失败" in message or "错误" in message:
            color = "#f48771"
        elif "⚠" in message or "警告" in message:
            color = "#dcdcaa"
        elif "正在" in message:
            color = "#569cd6"
        else:
            color = "#cccccc"
        
        self.append(f'<span style="color: {color};">{message}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear_log(self) -> None:
        self.clear()
