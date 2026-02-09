"""
Refactored UI widgets with COMPACT HORIZONTAL design.
"""

from typing import List, Set, Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
    QLabel, QFrame, QPushButton, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QCursor, QTextCursor

from core.scraped_data import ScrapedData, ResourceCategory
from core.models import Resource
from ui.i18n import t

class ResourceDetailDialog(QDialog):
    """
    Dialog to inspect and filter resources for a specific category.
    """
    def __init__(self, title: str, resources: List[Resource], selected_urls: Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        self.resources = resources
        self.selected_urls = set(selected_urls)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["", t('col_url'), t('col_filename'), t('col_size')])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        self._populate_table()
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_all = QPushButton(t('select_all'))
        self.btn_all.clicked.connect(self._select_all)
        btn_layout.addWidget(self.btn_all)
        
        self.btn_none = QPushButton("None / 无") 
        self.btn_none.clicked.connect(self._select_none)
        btn_layout.addWidget(self.btn_none)
        
        btn_layout.addStretch()
        
        self.btn_confirm = QPushButton(t('btn_confirm'))
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_confirm.setStyleSheet("background-color: #007acc; color: white; padding: 6px 15px; border-radius: 4px; font-weight: bold;")
        btn_layout.addWidget(self.btn_confirm)
        
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QTableWidget { background-color: #252526; color: white; border: 1px solid #333; gridline-color: #333; }
            QHeaderView::section { background-color: #333; color: white; padding: 4px; border: none; }
            QTableWidgetItem { padding: 5px; }
            QPushButton { background-color: #333; color: white; border: 1px solid #555; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background-color: #444; border-color: #00a0ff; }
        """)

    def _populate_table(self):
        self.table.setRowCount(len(self.resources))
        for i, res in enumerate(self.resources):
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            is_checked = res.url in self.selected_urls
            item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, item)
            self.table.setItem(i, 1, QTableWidgetItem(str(res.url)))
            self.table.setItem(i, 2, QTableWidgetItem(str(res.filename or "")))
            size_mb = res.size / (1024 * 1024) if res.size else 0
            size_str = f"{size_mb:.2f} MB" if size_mb > 0 else "Unknown"
            self.table.setItem(i, 3, QTableWidgetItem(size_str))
            
    def _select_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.CheckState.Checked)
            
    def _select_none(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.CheckState.Unchecked)
            
    def get_selected_urls(self) -> Set[str]:
        selected = set()
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                selected.add(self.resources[i].url)
        return selected


class CategoryCheckbox(QFrame):
    """
    Refactored category checkbox: Horizontal, Compact, Fixed Height.
    """
    
    stateChanged = pyqtSignal(int)
    detailsRequested = pyqtSignal()
    
    def __init__(self, icon: str, label_key: str, parent=None):
        super().__init__(parent)
        self.label_key = label_key
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # [修改] 强制高度 50px (非常紧凑，绝不会遮挡)
        self.setFixedHeight(50)
        # 水平扩展，垂直固定
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.setStyleSheet("""
            CategoryCheckbox {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
            }
            CategoryCheckbox:hover {
                background-color: #383838;
                border: 1px solid #00a0ff;
            }
        """)
        
        self._setup_ui(icon)
        
    def _setup_ui(self, icon: str):
        layout = QHBoxLayout(self)
        # [修改] 上下边距很小 (2px)，左右适中 (8px)
        layout.setContentsMargins(8, 2, 8, 2) 
        # [修改] 元素间距适中
        layout.setSpacing(8) 
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setTristate(True)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { border: 2px solid #888; background: #2a2a2a; border-radius: 3px; }
            QCheckBox::indicator:checked { border: 2px solid #00a0ff; background: #00a0ff; border-radius: 3px; }
            QCheckBox::indicator:indeterminate { border: 2px solid #00a0ff; background: #2a2a2a; border-radius: 3px; }
        """)
        self.checkbox.stateChanged.connect(self.stateChanged.emit) 
        layout.addWidget(self.checkbox)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setFixedSize(24, 24)
        icon_label.setFont(QFont("Segoe UI Emoji", 16)) 
        icon_label.setStyleSheet("background: transparent; border: none; color: #ffffff;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Text Label
        self.text_label = QLabel(t(self.label_key))
        # 字体稍微调小一点，防止换行
        self.text_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.text_label.setStyleSheet("color: #e0e0e0; background: transparent; border: none;")
        layout.addWidget(self.text_label, stretch=1)
        
        # Count Label
        self.count_label = QLabel("(0)")
        self.count_label.setFont(QFont("Microsoft YaHei", 10))
        self.count_label.setStyleSheet("color: #888; background: transparent; border: none;")
        layout.addWidget(self.count_label)
        
        # Details Button (Compact)
        self.details_btn = QPushButton(t('btn_details'))
        self.details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.details_btn.clicked.connect(self.detailsRequested.emit)
        self.details_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #ddd;
                border: 1px solid #555;
                padding: 2px 8px; /* 紧凑内边距 */
                border-radius: 3px;
                font-size: 11px;
                min-width: 40px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #555;
                color: white;
                border-color: #00a0ff;
            }
        """)
        self.details_btn.hide()
        layout.addWidget(self.details_btn)

    def update_text(self):
        """Update localized text."""
        self.text_label.setText(t(self.label_key))
        self.details_btn.setText(t('btn_details'))

    def set_count(self, count: int, total_str: str = "") -> None:
        """Update count display."""
        text = f"({count})" if not total_str else f"({count}/{total_str})"
        self.count_label.setText(text)
        
        if count > 0:
            self.setEnabled(True)
            self.count_label.setStyleSheet("color: #4ec9b0; background: transparent; border: none;")
            self.text_label.setStyleSheet("color: #ffffff; background: transparent; border: none; font-weight: bold;")
            self.details_btn.show()
        else:
            self.setEnabled(False)
            self.checkbox.setChecked(False)
            self.count_label.setStyleSheet("color: #666; background: transparent; border: none;")
            self.text_label.setStyleSheet("color: #999; background: transparent; border: none;")
            self.details_btn.hide()

    def set_check_state(self, state: Qt.CheckState):
        self.checkbox.setCheckState(state)

    def get_check_state(self) -> Qt.CheckState:
        return self.checkbox.checkState()


class CategoryPanel(QWidget):
    """
    Panel managing categories and their resources.
    """
    
    selection_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scraped_data: Optional[ScrapedData] = None
        
        # Mapping: category_key -> Set[url]
        self.selected_resources: Dict[str, Set[str]] = {
            'images': set(),
            'videos': set(),
            'documents': set()
        }
        
        self._setup_ui()
    
    def _setup_ui(self):
        # [重点] 恢复为横向布局 QHBoxLayout
        layout = QHBoxLayout(self)
        
        # [修改] 减少卡片之间的间距，防止在小屏幕上挤出屏幕
        layout.setSpacing(10)
        
        # [修改] 设置非常小的上下边距，把高度让给下面的组件
        layout.setContentsMargins(0, 5, 0, 10)
        
        # 设置 SizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Create checkboxes
        self.image_cb = CategoryCheckbox("🖼️", 'cat_images')
        self.video_cb = CategoryCheckbox("🎬", 'cat_videos')
        self.text_cb = CategoryCheckbox("📄", 'cat_documents')
        
        # Connect signals
        self.image_cb.stateChanged.connect(lambda s: self._on_cb_toggled('images', s))
        self.image_cb.detailsRequested.connect(lambda: self._show_details('images'))
        
        self.video_cb.stateChanged.connect(lambda s: self._on_cb_toggled('videos', s))
        self.video_cb.detailsRequested.connect(lambda: self._show_details('videos'))
        
        self.text_cb.stateChanged.connect(lambda s: self._on_cb_toggled('documents', s))
        self.text_cb.detailsRequested.connect(lambda: self._show_details('documents'))
        
        # Add widgets 
        layout.addWidget(self.image_cb)
        layout.addWidget(self.video_cb)
        layout.addWidget(self.text_cb)

    def update_texts(self):
        """Update language for all children."""
        self.image_cb.update_text()
        self.video_cb.update_text()
        self.text_cb.update_text()
    
    def display_results(self, data: ScrapedData) -> None:
        """Initialize with new data."""
        self.scraped_data = data
        
        def get_urls(r_list: List[Resource]) -> Set[str]:
            return {r.url for r in r_list if r.url}
            
        self.selected_resources['images'] = get_urls(data.images)
        all_videos = data.videos + data.m3u8_streams
        self.selected_resources['videos'] = get_urls(all_videos)
        all_docs = data.documents + data.audios
        self.selected_resources['documents'] = get_urls(all_docs)
        
        self._refresh_checkbox('images', len(data.images))
        self._refresh_checkbox('videos', len(all_videos))
        self._refresh_checkbox('documents', len(all_docs))

    def _refresh_checkbox(self, key: str, total_count: int):
        """Update checkbox state and count text based on selection."""
        cb = self._get_cb(key)
        selected_count = len(self.selected_resources[key])
        
        if selected_count == total_count:
            cb.set_count(total_count)
        else:
            cb.set_count(selected_count, str(total_count))
            
        cb.checkbox.blockSignals(True)
        if total_count == 0:
            cb.set_check_state(Qt.CheckState.Unchecked)
            cb.setEnabled(False) 
        elif selected_count == 0:
            cb.set_check_state(Qt.CheckState.Unchecked)
        elif selected_count == total_count:
            cb.set_check_state(Qt.CheckState.Checked)
        else:
            cb.set_check_state(Qt.CheckState.PartiallyChecked)
        cb.checkbox.blockSignals(False)

    def _get_cb(self, key: str) -> CategoryCheckbox:
        if key == 'images': return self.image_cb
        if key == 'videos': return self.video_cb
        return self.text_cb

    def _get_resources_list(self, key: str) -> List[Resource]:
        """Get full resource list for category."""
        if not self.scraped_data: return []
        if key == 'images': return self.scraped_data.images
        if key == 'videos': return self.scraped_data.videos + self.scraped_data.m3u8_streams
        if key == 'documents': return self.scraped_data.documents + self.scraped_data.audios
        return []

    def _on_cb_toggled(self, key: str, state: int):
        """Handle user clicking the checkbox."""
        resources = self._get_resources_list(key)
        all_urls = {r.url for r in resources}
        
        new_selection = set()
        if state == Qt.CheckState.Unchecked.value:
            new_selection = set()
        elif state == Qt.CheckState.Checked.value:
            new_selection = all_urls
        elif state == Qt.CheckState.PartiallyChecked.value:
            new_selection = all_urls
        
        self.selected_resources[key] = new_selection
        self._refresh_checkbox(key, len(resources))
        self.selection_changed.emit()

    def _show_details(self, key: str):
        """Open detailed inspection dialog."""
        resources = self._get_resources_list(key)
        if not resources: return
        
        title_map = {
            'images': t('cat_images'),
            'videos': t('cat_videos'),
            'documents': t('cat_documents')
        }
        title = t('details_title', title_map.get(key, key))
        
        dlg = ResourceDetailDialog(
            title,
            resources,
            self.selected_resources[key],
            self
        )
        
        if dlg.exec():
            self.selected_resources[key] = dlg.get_selected_urls()
            self._refresh_checkbox(key, len(resources))
            self.selection_changed.emit()

    def get_selected_map(self) -> Dict[str, Set[str]]:
        """Return the map of selected URLs."""
        return self.selected_resources
        
    def has_selection(self) -> bool:
        """Check if anything is selected."""
        return any(len(s) > 0 for s in self.selected_resources.values())


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