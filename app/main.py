"""
Application entry point for AI OCR Batch Image Renamer.
"""

import sys
import os
import ctypes

# Add root directory to sys.path to allow running as `python app/main.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui.main_window import MainWindow


def enable_windows_dpi_awareness():
    """Enables crisp text rendering on High-DPI Windows displays."""
    if sys.platform == "win32":
        try:
            # SetProcessDpiAwareness(2) for Per-Monitor DPI Aware or (1) for System DPI Aware
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main():
    enable_windows_dpi_awareness()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
