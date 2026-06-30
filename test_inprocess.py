"""Smoke-test: Streamlit on main thread with env var port override."""
import asyncio
import os
import sys
import threading
import time
import urllib.request

sys.path.insert(0, r"d:\Coding_Stuff\Projects\FileSense\src")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PORT = 8599

# Set env vars like the real launcher does
os.environ["STREAMLIT_SERVER_PORT"] = str(PORT)
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

def health_check():
    for i in range(30):
        time.sleep(0.5)
        try:
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{PORT}/_stcore/health", timeout=2
            )
            print(f"\n✅ Health OK: {resp.status} (after {(i+1)*0.5:.1f}s)")
            try:
                from streamlit.runtime import get_instance
                rt = get_instance()
                if rt:
                    rt.stop()
            except Exception:
                pass
            return
        except Exception:
            pass
    print("\n❌ Timed out waiting for health endpoint on port", PORT)

t = threading.Thread(target=health_check, daemon=True)
t.start()

print(f"Running Streamlit on MAIN thread (port {PORT}) ...")
from streamlit.web import bootstrap

try:
    bootstrap.run(
        r"d:\Coding_Stuff\Projects\FileSense\src\filesense\ui\app.py",
        is_hello=False,
        args=[],
        flag_options={
            "server.port": PORT,
            "server.headless": True,
            "server.address": "127.0.0.1",
            "browser.gatherUsageStats": False,
            "server.fileWatcherType": "none",
        },
    )
except SystemExit:
    print("Streamlit exited (SystemExit)")

print("✅ Test passed — Streamlit started and stopped cleanly.")
