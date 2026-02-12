#!/usr/bin/env python3
"""
Crawler - Production-Ready Web Resource Scraper

A PyQt6-based desktop application for intelligent web scraping with M3U8 support.

Copyright (C) 2026 Xustalis

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

Author: Xustalis
License: GPL v3
Version: 1.0.0
"""

import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from ui.styles import get_stylesheet
from utils.logger import setup_logger


# Setup logging
logger = setup_logger('Crawler')


class CrashHandler:
    """Global exception handler to ensure stability."""
    @staticmethod
    def install():
        sys.excepthook = CrashHandler.handle_exception

    @staticmethod
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Prepare crash report
        timestamp = __import__('datetime').datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        import platform
        system_info = (
            f"Platform: {platform.platform()}\n"
            f"Python: {sys.version}\n"
            f"Time: {timestamp}\n"
        )
        
        full_report = f"{system_info}\n{'='*40}\nCRASH REPORT\n{'='*40}\n{error_msg}"
        
        # Log to console/file via logger
        logger.critical(f"Uncaught exception:\n{error_msg}")
        
        # Save to crash log file
        try:
            log_dir = Path("crash_logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"crash_{timestamp}.txt"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(full_report)
            logger.info(f"Crash report saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save crash report: {e}")
        
        # Show error dialog if QApplication is active
        app = QApplication.instance()
        if app:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Application Crashed / 程序崩溃")
            msg.setInformativeText(f"An unexpected error occurred. / 发生意外错误。\nLog saved to: crash_logs/crash_{timestamp}.txt")
            msg.setDetailedText(error_msg)
            msg.setWindowTitle("Critical Error")
            msg.exec()



def main() -> int:
    """
    Application entry point.
    
    Returns:
        Exit code (0 for success)
    """
    try:
        # Enable High DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # Install global exception handler
        CrashHandler.install()
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Crawler")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("OpenSource")
        
        # Apply stylesheet
        app.setStyleSheet(get_stylesheet())
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Application started successfully")
        
        # Start event loop
        return app.exec()
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
