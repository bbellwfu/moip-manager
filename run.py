#!/usr/bin/env python3
"""Run the MoIP Manager web application."""
import sys
import threading
import time
import webbrowser
import os
import uvicorn
import config


def is_packaged() -> bool:
    """Check if running as a PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_menubar_icon_path() -> str:
    """Get the path to the menu bar icon."""
    # Use white icon - works for most macOS menu bars (dark by default)
    # TODO: Could add appearance detection in future if needed
    icon_name = "menubar_icon-wht.png"

    if is_packaged():
        return os.path.join(sys._MEIPASS, "app", "static", icon_name)
    else:
        return os.path.join(os.path.dirname(__file__), "app", "static", icon_name)


def open_browser(port: int):
    """Open the default browser to the web interface."""
    webbrowser.open(f"http://localhost:{port}")


def run_server(port: int):
    """Run the uvicorn server."""
    from app.main import app
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="warning",
    )


def run_with_tray(port: int):
    """Run the app with a system tray icon."""
    import pystray
    from PIL import Image

    # Load the menu bar icon
    icon_path = get_menubar_icon_path()
    try:
        icon_image = Image.open(icon_path)
    except Exception:
        # Fallback: create a simple colored icon
        icon_image = Image.new('RGB', (64, 64), color=(0, 120, 212))

    def on_open(icon, item):
        open_browser(port)

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)  # Force exit all threads

    # Create the menu
    menu = pystray.Menu(
        pystray.MenuItem(f"MoIP Manager", None, enabled=False),
        pystray.MenuItem(f"Running on port {port}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Web Interface", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    # Create the tray icon
    icon = pystray.Icon(
        "MoIP Manager",
        icon_image,
        "MoIP Manager",
        menu
    )

    # Start server in background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Open browser after short delay
    def delayed_open():
        time.sleep(1.5)
        open_browser(port)
    threading.Thread(target=delayed_open, daemon=True).start()

    # Run the tray icon (blocks until quit)
    icon.run()


if __name__ == "__main__":
    port = config.WEB_PORT

    if is_packaged():
        # Packaged app: run with system tray
        run_with_tray(port)
    else:
        # Development mode with reload
        uvicorn.run(
            "app.main:app",
            host=config.WEB_HOST,
            port=port,
            reload=True,
        )
