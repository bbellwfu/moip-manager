#!/usr/bin/env python3
"""Run the MoIP Manager web application."""
import sys
import threading
import time
import webbrowser
import uvicorn
import config


def is_packaged() -> bool:
    """Check if running as a PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def open_browser(port: int, delay: float = 1.5):
    """Open the default browser after a short delay."""
    def _open():
        time.sleep(delay)
        webbrowser.open(f"http://localhost:{port}")
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


if __name__ == "__main__":
    port = config.WEB_PORT

    # When packaged, auto-open browser and disable reload
    if is_packaged():
        open_browser(port)
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",  # Localhost only for packaged app
            port=port,
            reload=False,
            log_level="warning",
        )
    else:
        # Development mode with reload and all interfaces
        uvicorn.run(
            "app.main:app",
            host=config.WEB_HOST,
            port=port,
            reload=True,
        )
