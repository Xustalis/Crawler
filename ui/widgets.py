"""
Custom widgets for the Crawler application.

Provides reusable UI components with proper encapsulation.
"""

from typing import List

from PyQt6.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QTextEdit,
    QCheckBox, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor

from core.models import Resource, ResourceType, DownloadStatus
from ui.i18n import t


class ResourceListWidget(QWidget):
    """
    Custom widget for displaying and selecting resources.
    
    Features:
    - Checkbox for each resource
    - Resource type icons
    - Progress bars for downloads
    """
    
    selection_changed = pyqtSignal()  # Emitted when selection changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resources: List[Resource] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        self.header = QLabel(t('resources_title'))
        self.header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.header)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_widget)
        
        # Select all checkbox
        self.select_all_cb = QCheckBox(t('select_all'))
        self.select_all_cb.stateChanged.connect(self._on_select_all)
        layout.addWidget(self.select_all_cb)
    
    def set_resources(self, resources: List[Resource]) -> None:
        """
        Populate list with resources.
        
        Args:
            resources: List of Resource objects
        """
        self.resources = resources
        self.list_widget.clear()
        
        for resource in resources:
            item_widget = ResourceItemWidget(resource)
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)
    
    def get_selected_resources(self) -> List[Resource]:
        """
        Get list of selected resources.
        
        Returns:
            List of selected Resource objects
        """
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, ResourceItemWidget) and widget.is_selected():
                selected.append(widget.resource)
        return selected
    
    def update_resource_progress(self, resource: Resource, progress: float) -> None:
        """Update progress bar for a specific resource."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, ResourceItemWidget) and widget.resource == resource:
                widget.set_progress(progress)
                break
    
    def _on_select_all(self, state: int) -> None:
        """Handle select all checkbox."""
        select = (state == Qt.CheckState.Checked.value)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, ResourceItemWidget):
                widget.set_selected(select)
    
    def update_language(self) -> None:
        """Update widget texts when language changes."""
        self.header.setText(t('resources_title'))
        self.select_all_cb.setText(t('select_all'))


class ResourceItemWidget(QWidget):
    """Individual resource item with checkbox and info."""
    
    def __init__(self, resource: Resource, parent=None):
        super().__init__(parent)
        self.resource = resource
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Top row: checkbox and title
        top_layout = QHBoxLayout()
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        top_layout.addWidget(self.checkbox)
        
        # Type icon
        icon = self._get_type_icon(self.resource.resource_type)
        type_label = QLabel(icon)
        top_layout.addWidget(type_label)
        
        # Title
        title = self.resource.title[:80] + "..." if len(self.resource.title) > 80 else self.resource.title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e0e0e0;")
        top_layout.addWidget(title_label, stretch=1)
        
        layout.addLayout(top_layout)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
    
    def _get_type_icon(self, resource_type: ResourceType) -> str:
        """Get emoji icon for resource type."""
        icons = {
            ResourceType.VIDEO: "🎬",
            ResourceType.M3U8: "📺",
            ResourceType.IMAGE: "🖼️",
            ResourceType.AUDIO: "🎵",
            ResourceType.TEXT: "📄",
            ResourceType.UNKNOWN: "❓"
        }
        return icons.get(resource_type, "📦")
    
    def is_selected(self) -> bool:
        """Check if resource is selected."""
        return self.checkbox.isChecked()
    
    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self.checkbox.setChecked(selected)
    
    def set_progress(self, progress: float) -> None:
        """
        Update progress bar.
        
        Args:
            progress: Progress value (0.0 to 1.0)
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(int(progress * 100))


class LogWidget(QTextEdit):
    """
    Custom log widget with auto-scrolling and color coding.
    
    Thread-safe log message display.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(200)
        
    def append_log(self, message: str) -> None:
        """
        Append log message with auto-scroll.
        
        Args:
            message: Log message to append
        """
        # Color code messages
        if message.startswith("✓"):
            color = "#4ec9b0"  # Success - cyan
        elif message.startswith("✗"):
            color = "#f48771"  # Error - red
        elif "error" in message.lower() or "failed" in message.lower():
            color = "#f48771"
        elif "warning" in message.lower():
            color = "#dcdcaa"  # Warning - yellow
        else:
            color = "#cccccc"  # Default - light gray
        
        html = f'<span style="color: {color};">{message}</span>'
        self.append(html)
        
        # Auto-scroll to bottom
        self.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear_log(self) -> None:
        """Clear all log messages."""
        self.clear()
