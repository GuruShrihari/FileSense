"""
FileSense Desktop Launcher.

Orchestrates the Streamlit server and pywebview window to present
FileSense as a native desktop application with no browser exposure.
"""

from __future__ import annotations

import atexit
import logging
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("filesense.launcher")

_APP_TITLE = "FileSense"
_HEALTH_ENDPOINT = "/_stcore/health"
_STARTUP_TIMEOUT_SECONDS = 120
_HEALTH_POLL_INTERVAL_SECONDS = 0.5
_WINDOW_WIDTH = 1280
_WINDOW_HEIGHT = 800


def _find_free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _resolve_streamlit_app_path() -> str:
    """Resolve the absolute path to the Streamlit UI script (app.py).

    Handles both normal Python execution and PyInstaller frozen bundles.
    """
    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parent

    app_path = base_dir / "ui" / "app.py"

    if not app_path.exists():
        raise FileNotFoundError(
            f"Streamlit app not found at {app_path}. "
            "Ensure src/filesense/ui/app.py exists."
        )

    return str(app_path)


class StreamlitServer:
    """Manages the Streamlit subprocess lifecycle."""

    def __init__(self, port: int, app_path: str, config_dir: Path) -> None:
        self.port = port
        self.app_path = app_path
        self.config_dir = config_dir
        self._process: Optional[subprocess.Popen] = None  # type: ignore[type-arg]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def health_url(self) -> str:
        return f"{self.url}{_HEALTH_ENDPOINT}"

    def start(self) -> None:
        """Launch the Streamlit server as a subprocess."""
        env = os.environ.copy()
        env["STREAMLIT_CONFIG_DIR"] = str(self.config_dir / ".streamlit")
        env["STREAMLIT_SERVER_HEADLESS"] = "true"
        env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        env["STREAMLIT_SERVER_PORT"] = str(self.port)
        env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
        env["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
        env["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
        env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

        cmd = [sys.executable, "-m", "streamlit", "run", self.app_path,
               "--server.port", str(self.port),
               "--server.headless", "true",
               "--browser.gatherUsageStats", "false",
               "--server.fileWatcherType", "none"]

        logger.info("Starting Streamlit: %s", " ".join(cmd))

        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        self._process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation_flags,
        )

        atexit.register(self.stop)
        logger.info("Streamlit process started (PID %d)", self._process.pid)

    def wait_until_ready(self, timeout: float = _STARTUP_TIMEOUT_SECONDS) -> bool:
        """Block until the Streamlit health endpoint responds 200."""
        start_time = time.monotonic()
        logger.info("Waiting for Streamlit at %s ...", self.health_url)

        while (time.monotonic() - start_time) < timeout:
            if self._process and self._process.poll() is not None:
                rc = self._process.returncode
                stderr_output = ""
                if self._process.stderr:
                    stderr_output = self._process.stderr.read().decode(errors="replace")
                logger.error(
                    "Streamlit exited prematurely (code %d): %s", rc, stderr_output[:500],
                )
                return False

            try:
                req = urllib.request.Request(self.health_url, method="GET")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        logger.info("Streamlit is ready.")
                        return True
            except (urllib.error.URLError, OSError, ConnectionError):
                pass

            time.sleep(_HEALTH_POLL_INTERVAL_SECONDS)

        logger.error("Streamlit did not become ready within %ds", timeout)
        return False

    def stop(self) -> None:
        """Terminate the Streamlit subprocess and its entire process tree."""
        if self._process is None:
            return

        logger.info("Stopping Streamlit (PID %d) ...", self._process.pid)

        try:
            if platform.system() == "Windows":
                subprocess.call(
                    ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass

        self._process = None
        logger.info("Streamlit stopped.")

    def cleanup_config(self) -> None:
        """Remove the temporary config directory."""
        try:
            if self.config_dir.exists():
                shutil.rmtree(self.config_dir, ignore_errors=True)
        except Exception:
            pass


def _show_error_dialog(title: str, message: str) -> None:
    """Show a native error dialog using tkinter (stdlib fallback)."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"ERROR: {title}\n{message}", file=sys.stderr)


def launch() -> None:
    """Main entry point for the FileSense desktop application."""
    try:
        import webview  # noqa: F401
    except ImportError:
        _show_error_dialog(
            "Missing Dependency",
            "pywebview is required but not installed.\n\n"
            "Install it with: pip install pywebview"
        )
        sys.exit(1)

    port = _find_free_port()
    logger.info("Using port %d", port)

    from filesense.desktop_config import create_streamlit_config
    config_dir = Path(create_streamlit_config(port))
    logger.info("Config directory: %s", config_dir)

    try:
        app_path = _resolve_streamlit_app_path()
    except FileNotFoundError as exc:
        _show_error_dialog("FileSense Error", str(exc))
        sys.exit(1)

    server = StreamlitServer(port=port, app_path=app_path, config_dir=config_dir)

    try:
        server.start()
    except Exception as exc:
        _show_error_dialog(
            "Startup Error",
            f"Failed to start the Streamlit server:\n\n{exc}"
        )
        sys.exit(1)

    if not server.wait_until_ready():
        server.stop()
        server.cleanup_config()
        _show_error_dialog(
            "Startup Error",
            "FileSense failed to start.\n\n"
            "The internal server did not respond within the timeout period.\n"
            "Check the logs for details."
        )
        sys.exit(1)

    logger.info("Opening pywebview window → %s", server.url)

    try:
        webview.create_window(
            title=_APP_TITLE,
            url=server.url,
            width=_WINDOW_WIDTH,
            height=_WINDOW_HEIGHT,
            resizable=True,
            min_size=(800, 600),
            text_select=True,
        )

        # Blocking — returns when the window is closed
        webview.start(debug=False)
    except Exception as exc:
        logger.exception("pywebview error")
        _show_error_dialog("Display Error", f"Failed to create window:\n\n{exc}")
    finally:
        server.stop()
        server.cleanup_config()
        logger.info("FileSense shut down cleanly.")


if __name__ == "__main__":
    launch()
