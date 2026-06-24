# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FileSense Desktop. Run: pyinstaller filesense.spec"""

import os
from pathlib import Path

SPEC_DIR = os.path.abspath(SPECPATH)  # noqa: F821
SRC_DIR = os.path.join(SPEC_DIR, "src")

# Streamlit ships a React frontend that must be bundled
import streamlit
streamlit_dir = Path(streamlit.__file__).parent
streamlit_static = str(streamlit_dir / "static")

# Bundle the sentence-transformers model cache if present
MODEL_NAME = "sentence-transformers_all-MiniLM-L6-v2"
POSSIBLE_CACHE_DIRS = [
    Path.home() / ".cache" / "torch" / "sentence_transformers" / MODEL_NAME,
    Path.home() / ".cache" / "huggingface" / "hub",
]

model_datas = []
for cache_dir in POSSIBLE_CACHE_DIRS:
    if cache_dir.exists():
        model_datas.append((str(cache_dir), str(cache_dir.relative_to(Path.home() / ".cache"))))
        break

datas = [
    (streamlit_static, "streamlit/static"),
    (os.path.join(SRC_DIR, "filesense"), "filesense"),
] + model_datas

hiddenimports = [
    "streamlit", "streamlit.web", "streamlit.web.cli",
    "streamlit.web.server", "streamlit.web.server.server",
    "streamlit.runtime", "streamlit.runtime.scriptrunner",
    "streamlit.runtime.caching", "streamlit.components.v1",
    "tornado", "tornado.web", "tornado.websocket",
    "tornado.ioloop", "tornado.httpserver",
    "filesense", "filesense.ui", "filesense.ui.app",
    "filesense.core", "filesense.core.scanner",
    "filesense.core.scanner.scan", "filesense.core.scanner.filters",
    "filesense.core.extractor", "filesense.core.extractor.text",
    "filesense.core.embeddings", "filesense.core.embeddings.model",
    "filesense.core.embeddings.index", "filesense.core.analysis",
    "filesense.core.analysis.safety_score", "filesense.core.analysis.duplicates",
    "filesense.desktop_config", "filesense.launcher",
    "sentence_transformers", "torch", "numpy", "faiss",
    "transformers", "huggingface_hub", "tokenizers",
    "PyPDF2", "docx", "pandas", "pyarrow", "webview",
    "packaging", "packaging.version", "packaging.specifiers",
    "packaging.requirements", "importlib_metadata",
    "altair", "pydeck", "toml",
]

a = Analysis(
    [os.path.join(SRC_DIR, "filesense", "launcher.py")],
    pathex=[SRC_DIR],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "matplotlib", "scipy", "PIL", "cv2",
        "IPython", "notebook", "jupyter",
        "tkinter.test", "test", "tests",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="FileSense",
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=True,
    name="FileSense",
)
