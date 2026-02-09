"""
QSS (Qt Style Sheets) for modern, professional UI styling.

Provides a clean, cyberpunk-inspired dark theme.
"""


def get_stylesheet() -> str:
    """
    Get the application stylesheet.
    
    Returns:
        QSS stylesheet string
    """
    return """
    /* Main Window */
    QMainWindow {
        background-color: #1e1e1e;
    }
    
    /* Labels */
    QLabel {
        color: #e0e0e0;
        font-size: 13px;
    }
    
    /* Line Edit */
    QLineEdit {
        background-color: #2d2d30;
        border: 1px solid #3f3f46;
        border-radius: 4px;
        padding: 8px;
        color: #e0e0e0;
        font-size: 13px;
        selection-background-color: #007acc;
    }
    
    QLineEdit:focus {
        border: 1px solid #007acc;
    }
    
    /* Push Button */
    QPushButton {
        background-color: #0e639c;
        border: none;
        border-radius: 4px;
        color: white;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }
    
    QPushButton:hover {
        background-color: #1177bb;
    }
    
    QPushButton:pressed {
        background-color: #0d5a8a;
    }
    
    QPushButton:disabled {
        background-color: #3f3f46;
        color: #6e6e6e;
    }
    
    /* Secondary Buttons */
    QPushButton#secondaryButton {
        background-color: #2d2d30;
        border: 1px solid #3f3f46;
        color: #e0e0e0;
    }
    
    QPushButton#secondaryButton:hover {
        background-color: #3e3e42;
    }
    
    /* Text Edit / Log */
    QTextEdit {
        background-color: #1e1e1e;
        border: 1px solid #3f3f46;
        border-radius: 4px;
        color: #cccccc;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        padding: 8px;
    }
    
    /* List Widget */
    QListWidget {
        background-color: #252526;
        border: 1px solid #3f3f46;
        border-radius: 4px;
        color: #e0e0e0;
        font-size: 13px;
        outline: none;
    }
    
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #2d2d30;
    }
    
    QListWidget::item:selected {
        background-color: #094771;
    }
    
    QListWidget::item:hover {
        background-color: #2a2d2e;
    }
    
    /* Checkbox */
    QCheckBox {
        color: #e0e0e0;
        spacing: 8px;
        font-size: 13px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 1px solid #3f3f46;
        background-color: #2d2d30;
    }
    
    QCheckBox::indicator:checked {
        background-color: #007acc;
        border-color: #007acc;
    }
    
    /* Progress Bar */
    QProgressBar {
        border: 1px solid #3f3f46;
        border-radius: 4px;
        text-align: center;
        background-color: #2d2d30;
        color: #e0e0e0;
        font-size: 12px;
        height: 20px;
    }
    
    QProgressBar::chunk {
        background-color: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 #007acc,
            stop: 1 #00a0ff
        );
        border-radius: 3px;
    }
    
    /* Scroll Bar */
    QScrollBar:vertical {
        background-color: #1e1e1e;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #3f3f46;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #4f4f56;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    /* Status Bar */
    QStatusBar {
        background-color: #007acc;
        color: white;
        font-weight: bold;
        font-size: 12px;
    }
    
    /* Group Box */
    QGroupBox {
        color: #e0e0e0;
        border: 1px solid #3f3f46;
        border-radius: 4px;
        margin-top: 12px;
        font-weight: bold;
        padding-top: 10px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
    """
