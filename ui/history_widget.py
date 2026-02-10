
from typing import Optional
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QPushButton, QHBoxLayout, QMessageBox, 
    QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QColor, QDesktopServices
from PyQt6.QtCore import QUrl   

from core.database import DatabaseManager
from ui.i18n import t

class HistoryWidget(QWidget):
    """
    Widget to display crawl history from database.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self._setup_ui()
        self.load_history()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tools
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh / 刷新")
        self.refresh_btn.clicked.connect(self.load_history)
        btn_layout.addWidget(self.refresh_btn)
        
        self.open_dir_btn = QPushButton("Open Folder / 打开目录")
        self.open_dir_btn.clicked.connect(self._open_selected_folder)
        btn_layout.addWidget(self.open_dir_btn)
        
        btn_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear All / 清空记录")
        self.clear_btn.setStyleSheet("background-color: #d9534f; color: white; border: none; padding: 5px 10px; border-radius: 4px;")
        self.clear_btn.clicked.connect(self._clear_all_history)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "URL", "Status", "Progress", "Date", "Path"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._open_selected_folder)
        
        layout.addWidget(self.table)
        
        self.setStyleSheet("""
            QTableWidget {
                background-color: #252526;
                color: #e0e0e0;
                border: 1px solid #333;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #333;
                color: #e0e0e0;
                padding: 4px;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
            }
        """)

    def load_history(self):
        """Reload data from DB."""
        tasks = self.db.get_all_tasks()
        self.table.setRowCount(0)
        
        for row, task in enumerate(tasks):
            self.table.insertRow(row)
            
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(task['id'])))
            
            # URL
            self.table.setItem(row, 1, QTableWidgetItem(task['source_url']))
            
            # Status
            status_item = QTableWidgetItem(task['status'])
            if task['status'] == 'completed' or task['status'] == 'scanned':
                status_item.setForeground(QColor("#4ec9b0"))
            elif task['status'] == 'failed':
                status_item.setForeground(QColor("#f48771"))
            self.table.setItem(row, 2, status_item)
            
            # Progress
            total = task['total_items'] or 0
            done = task['downloaded_items'] or 0
            prog_str = f"{done}/{total}" if total > 0 else "-"
            self.table.setItem(row, 3, QTableWidgetItem(prog_str))
            
            # Date
            created = task['created_at']
            date_str = str(created)
            if isinstance(created, str):
                try:
                     # Attempt to clean up Z or T if present
                     date_str = created.replace('T', ' ').split('.')[0]
                except:
                     pass
            self.table.setItem(row, 4, QTableWidgetItem(date_str))
            
            # Path
            path_item = QTableWidgetItem(task['save_path'])
            path_item.setData(Qt.ItemDataRole.UserRole, task['save_path'])
            self.table.setItem(row, 5, path_item)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        
        open_action = QAction("Open Folder", self)
        open_action.triggered.connect(self._open_selected_folder)
        menu.addAction(open_action)
        
        delete_action = QAction("Delete Record", self)
        delete_action.triggered.connect(self._delete_selected_task)
        menu.addAction(delete_action)
        
        menu.exec(self.table.mapToGlobal(pos))

    def _open_selected_folder(self):
        row = self.table.currentRow()
        if row < 0:
            return
            
        path_item = self.table.item(row, 5)
        if path_item:
            path = path_item.data(Qt.ItemDataRole.UserRole)
            if path and os.path.exists(path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            else:
                QMessageBox.warning(self, "Error", f"Folder not found: {path}\n(It might have been deleted, feel free to delete the history record)")

    def _delete_selected_task(self):
        row = self.table.currentRow()
        if row < 0: return
        
        task_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(self, 'Confirm Delete', f"Delete history for Task ID {task_id}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_task(task_id)
            self.load_history()

    def _clear_all_history(self):
        reply = QMessageBox.question(self, 'Confirm Clear', "Are you sure you want to clear ALL history?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_all_tasks()
            self.load_history()

