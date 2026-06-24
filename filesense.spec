# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FileSense Desktop Application.

Builds a one-directory distribution containing the Streamlit app,
all Python dependencies, and the sentence-transformers model.

Usage:
    pyinstaller filesense.spec

Output:
    dist/FileSense/FileSense.exe
"""

import os
import sys
import importlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SPEC_DIR = os.path.abspath(SPECPATH)  # noqa: F821  (SPECPATH is a PyInstaller global)
SRC_DIR = os.path.join(SPEC_DIR, "src")

# ---------------------------------------------------------------------------
# Collect Streamlit's static web assets
# ---------------------------------------------------------------------------
# Streamlit ships with a full React frontend that must be included.

import streamlit
streamlit_dir = Path(streamlit.__file__).parent
streamlit_static = str(streamlit_dir / "static")

# ---------------------------------------------------------------------------
# Locate the sentence-transformers model cache
# ---------------------------------------------------------------------------
# The model is typically cached at:
#   ~/.cache/torch/sentence_transformers/  (Linux)
#   %USERPROFILE%/.cache/torch/sentence_transformers/  (Windows)
#
# We bundle the default model so it works offline in the packaged app.

MODEL_NAME = "sentence-transformers_all-MiniLM-L6-v2"
POSSIBLE_CACHE_DIRS = [
    Path.home() / ".cache" / "torch" / "sentence_transformers" / MODEL_NAME,
    Path.home() / ".cache" / "huggingface" / "hub",
]

model_datas = []
for cache_dir in POSSIBLE_CACHE_DIRS:
    if cache_dir.exists():
        # Bundle the model files into a matching directory structure
        model_datas.append((str(cache_dir), str(cache_dir.relative_to(Path.home() / ".cache"))))
        break

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------

datas = [
    # Streamlit static frontend (React app)
    (streamlit_static, "streamlit/static"),
    # Our Streamlit app source
    (os.path.join(SRC_DIR, "filesense"), "filesense"),
]

# Add model cache if found
datas.extend(model_datas)

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
# Packages that PyInstaller's static analysis misses because they are
# imported dynamically at runtime.

hiddenimports = [
    # Streamlit internals
    "streamlit",
    "streamlit.web",
    "streamlit.web.cli",
    "streamlit.web.server",
    "streamlit.web.server.server",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.caching",
    "streamlit.components.v1",

    # Tornado (Streamlit's web server)
    "tornado",
    "tornado.web",
    "tornado.websocket",
    "tornado.ioloop",
    "tornado.httpserver",

    # Our app modules
    "filesense",
    "filesense.ui",
    "filesense.ui.app",
    "filesense.core",
    "filesense.core.scanner",
    "filesense.core.scanner.scan",
    "filesense.core.scanner.filters",
    "filesense.core.extractor",
    "filesense.core.extractor.text",
    "filesense.core.embeddings",
    "filesense.core.embeddings.model",
    "filesense.core.embeddings.index",
    "filesense.core.analysis",
    "filesense.core.analysis.safety_score",
    "filesense.core.analysis.duplicates",
    "filesense.desktop_config",
    "filesense.launcher",

    # ML stack
    "sentence_transformers",
    "torch",
    "numpy",
    "faiss",
    "transformers",
    "huggingface_hub",
    "tokenizers",

    # Document parsing
    "PyPDF2",
    "docx",

    # Data
    "pandas",
    "pyarrow",

    # pywebview backends
    "webview",

    # Misc runtime deps
    "packaging",
    "packaging.version",
    "packaging.specifiers",
    "packaging.requirements",
    "importlib_metadata",
    "altair",
    "pydeck",
    "toml",
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    [os.path.join(SRC_DIR, "filesense", "launcher.py")],
    pathex=[SRC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary heavy packages to reduce size
        "matplotlib",
        "scipy",
        "PIL",
        "cv2",
        "IPython",
        "notebook",
        "jupyter",
        "tkinter.test",
        "test",
        "tests",
    ],
    noarchive=False,
)

# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FileSense",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/filesense.ico",  # Uncomment when icon is available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FileSense",
)
