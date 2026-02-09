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
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from ui.styles import get_stylesheet
from utils.logger import setup_logger


# Setup logging
logger = setup_logger('Crawler')


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
