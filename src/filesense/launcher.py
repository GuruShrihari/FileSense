"""
FileSense Desktop Launcher.

Orchestrates the Streamlit server and pywebview window to present
FileSense as a native desktop application with no browser exposure.

Architecture
~~~~~~~~~~~~
Streamlit's bootstrap *must* run on the **main thread** because it
installs signal handlers (which Python restricts to the main thread).
Therefore pywebview runs in a background thread instead.

This also eliminates the PyInstaller fork-bomb: no subprocess is spawned
at all, so ``sys.executable`` pointing to the ``.exe`` is irrelevant.
"""

from __future__ import annotations

import asyncio
import atexit
import ctypes
import http.client
import logging
import os
import platform
import shutil
import socket
import sys
import threading
import time
import traceback
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
#  Logging — write to a file so we always have diagnostics even when the
#  .exe is built with console=False.
# ---------------------------------------------------------------------------
_LOG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "FileSense"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "launcher.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("filesense.launcher")
logger.info("=== FileSense Launcher starting ===")
logger.info(
    "Python %s | frozen=%s | platform=%s",
    sys.version, getattr(sys, "frozen", False), platform.platform(),
)
if getattr(sys, "frozen", False):
    logger.info("_MEIPASS = %s", getattr(sys, "_MEIPASS", "N/A"))

_APP_TITLE = "FileSense"
_HEALTH_ENDPOINT = "/_stcore/health"
_STARTUP_TIMEOUT_SECONDS = 120
_HEALTH_POLL_INTERVAL_SECONDS = 0.5
_WINDOW_WIDTH = 1280
_WINDOW_HEIGHT = 800


# =========================================================================
#  Utility helpers
# =========================================================================

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
        base_dir = Path(sys._MEIPASS) / "filesense"  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parent

    app_path = base_dir / "ui" / "app.py"

    if not app_path.exists():
        raise FileNotFoundError(
            f"Streamlit app not found at {app_path}. "
            "Ensure src/filesense/ui/app.py exists."
        )

    return str(app_path)


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


def _acquire_single_instance_lock() -> bool:
    """On Windows, create a named mutex to enforce single-instance.

    Returns True if we acquired the lock (we're the first instance).
    Returns False if another instance already holds it.
    On non-Windows platforms, always returns True.
    """
    if platform.system() != "Windows":
        return True

    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        mutex_name = "Global\\FileSense_SingleInstance_Mutex"
        handle = kernel32.CreateMutexW(None, True, mutex_name)
        last_error = kernel32.GetLastError()

        if handle == 0 or last_error == 183:  # ERROR_ALREADY_EXISTS
            logger.warning("Another FileSense instance is already running.")
            return False
        return True
    except Exception:
        return True


def _wait_for_health(url: str, timeout: float = _STARTUP_TIMEOUT_SECONDS) -> bool:
    """Block until the Streamlit health endpoint responds 200."""
    start = time.monotonic()
    logger.info("Waiting for Streamlit at %s ...", url)

    while (time.monotonic() - start) < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    logger.info("Streamlit is ready.")
                    return True
        except (urllib.error.URLError, OSError, ConnectionError,
                http.client.HTTPException):
            pass
        time.sleep(_HEALTH_POLL_INTERVAL_SECONDS)

    logger.error("Streamlit did not become ready within %ds", timeout)
    return False


# =========================================================================
#  Launch
# =========================================================================

def launch() -> None:
    """Main entry point for the FileSense desktop application."""

    # --- Guard: single-instance enforcement ---
    if not _acquire_single_instance_lock():
        _show_error_dialog(
            "Already Running",
            "FileSense is already running.\n\n"
            "Check your taskbar or system tray."
        )
        sys.exit(0)

    try:
        import webview  # noqa: F401
    except ImportError:
        _show_error_dialog(
            "Missing Dependency",
            "pywebview is required but not installed.\n\n"
            "Install it with: pip install pywebview"
        )
        sys.exit(1)

    # ---- Event loop policy (must be set before any loop is created) ----
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    port = _find_free_port()
    logger.info("Using port %d", port)

    from filesense.desktop_config import create_streamlit_config
    config_dir = Path(create_streamlit_config(port))
    logger.info("Config directory: %s", config_dir)

    try:
        app_path = _resolve_streamlit_app_path()
        logger.info("Resolved app path: %s", app_path)
    except FileNotFoundError as exc:
        _show_error_dialog("FileSense Error", str(exc))
        sys.exit(1)

    # ---- Configure Streamlit via env vars ----------------------------
    os.environ["STREAMLIT_CONFIG_DIR"] = str(config_dir / ".streamlit")
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
    os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

    server_url = f"http://127.0.0.1:{port}"
    health_url = f"{server_url}{_HEALTH_ENDPOINT}"

    flag_options = {
        "server.port": port,
        "server.headless": True,
        "server.address": "127.0.0.1",
        "browser.gatherUsageStats": False,
        "server.enableCORS": False,
        "server.enableXsrfProtection": False,
        "server.fileWatcherType": "none",
        "server.maxUploadSize": 200,
        "global.developmentMode": False,
    }

    # ---- Import bootstrap (fail fast with a clear message) -----------
    try:
        from streamlit.web import bootstrap
    except ImportError as exc:
        _show_error_dialog(
            "Missing Dependency",
            f"Failed to import Streamlit bootstrap:\n\n{exc}"
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Architecture (Windows-correct):
    #   Main thread  →  pywebview (MUST be main thread on Windows for
    #                    the native window message loop / COM)
    #   BG thread    →  Streamlit (signal handlers degrade gracefully;
    #                    they only log a warning, they don't crash)
    # ------------------------------------------------------------------
    streamlit_error: Optional[str] = None

    def _streamlit_thread() -> None:
        """Run Streamlit's bootstrap in a background thread."""
        nonlocal streamlit_error
        try:
            # Monkey-patch: Streamlit's _set_up_signal_handler calls
            # signal.signal() which raises ValueError in non-main threads.
            # Replace it with a no-op so the server can start normally.
            import streamlit.web.bootstrap as _bs
            _bs._set_up_signal_handler = lambda server: None
            logger.info("[streamlit thread] Patched signal handler (non-main thread)")

            # Force config via set_option — flag_options alone may not apply
            # before the Server reads its config.
            from streamlit import config as _st_config
            for key, value in flag_options.items():
                try:
                    _st_config.set_option(key, value)
                except Exception as e:
                    logger.debug("Could not set_option(%s): %s", key, e)

            # In frozen bundles, Streamlit needs to find its static assets.
            # Ensure the source root is on sys.path so imports resolve.
            if getattr(sys, "frozen", False):
                meipass = getattr(sys, "_MEIPASS", None)
                if meipass and meipass not in sys.path:
                    sys.path.insert(0, meipass)
                    logger.info("[streamlit thread] Added _MEIPASS to sys.path: %s", meipass)

            logger.info("[streamlit thread] Starting bootstrap.run (app=%s) ...", app_path)
            bootstrap.run(
                app_path,
                is_hello=False,
                args=[],
                flag_options=flag_options,
            )
            logger.info("[streamlit thread] bootstrap.run returned normally")
        except SystemExit as exc:
            code = getattr(exc, "code", None)
            logger.info("[streamlit thread] Exited (code=%s)", code)
        except Exception as exc:
            streamlit_error = str(exc)
            logger.exception("[streamlit thread] Streamlit crashed")
            # Also write to stderr for frozen builds
            traceback.print_exc()

    def _stop_streamlit() -> None:
        """Best-effort stop of the Streamlit runtime."""
        try:
            from streamlit.runtime import get_instance  # type: ignore[import]
            runtime = get_instance()
            if runtime is not None:
                runtime.stop()
        except Exception:
            logger.debug("Could not stop Streamlit via runtime API", exc_info=True)

        # Clean up temp config
        try:
            if config_dir.exists():
                shutil.rmtree(config_dir, ignore_errors=True)
        except Exception:
            pass

    # Start Streamlit in a background daemon thread
    st_thread = threading.Thread(
        target=_streamlit_thread, name="streamlit", daemon=True,
    )
    st_thread.start()

    # ------------------------------------------------------------------
    # Wait for the Streamlit health endpoint on the MAIN thread,
    # then open the pywebview window (must be main thread on Windows).
    # ------------------------------------------------------------------
    logger.info("Waiting for Streamlit health on main thread ...")
    if not _wait_for_health(health_url):
        _show_error_dialog(
            "Startup Error",
            "FileSense failed to start.\n\n"
            "The internal server did not respond within the "
            "timeout period.\n\n"
            f"Log file: {_LOG_FILE}",
        )
        _stop_streamlit()
        sys.exit(1)

    logger.info("Streamlit is ready — opening pywebview window → %s", server_url)
    try:
        window = webview.create_window(
            title=_APP_TITLE,
            url=server_url,
            width=_WINDOW_WIDTH,
            height=_WINDOW_HEIGHT,
            resizable=True,
            min_size=(800, 600),
            text_select=True,
            on_top=True,  # Force to foreground initially
        )

        def _on_shown():
            """Once visible, disable always-on-top and bring to focus."""
            try:
                time.sleep(1)
                if window is not None:
                    window.on_top = False
            except Exception:
                pass

        # webview.start() blocks until ALL windows are closed
        webview.start(func=_on_shown, debug=False)
    except Exception as exc:
        logger.exception("pywebview error")
        _show_error_dialog(
            "Window Error",
            f"Failed to create the application window:\n\n{exc}",
        )
    finally:
        logger.info("Window closed — stopping Streamlit server")
        _stop_streamlit()
        st_thread.join(timeout=5)

        if streamlit_error:
            _show_error_dialog(
                "Server Error",
                f"Streamlit server crashed:\n\n{streamlit_error}\n\n"
                f"Log file: {_LOG_FILE}",
            )

        logger.info("FileSense shut down cleanly.")


if __name__ == "__main__":
    launch()
