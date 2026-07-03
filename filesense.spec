# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FileSense Desktop. Run: pyinstaller filesense.spec"""

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

SPEC_DIR = os.path.abspath(SPECPATH)  # noqa: F821
SRC_DIR = os.path.join(SPEC_DIR, "src")

# Streamlit ships a React frontend that must be bundled
import streamlit
streamlit_dir = Path(streamlit.__file__).parent
streamlit_static = str(streamlit_dir / "static")

# Collect ALL streamlit artifacts (metadata, datas, hidden imports)
sl_datas, sl_binaries, sl_hiddenimports = collect_all("streamlit")

# Collect sentence-transformers and its heavy dependencies
st_datas, st_binaries, st_hiddenimports = collect_all("sentence_transformers")
tf_datas, tf_binaries, tf_hiddenimports = collect_all("transformers")
tk_datas, tk_binaries, tk_hiddenimports = collect_all("tokenizers")

# Also collect metadata for packages inspected at runtime
extra_metadata = []
for pkg in ["streamlit", "altair", "pydeck", "packaging", "importlib_metadata",
            "sentence-transformers", "transformers", "tokenizers", "torch",
            "huggingface-hub", "numpy", "tqdm", "safetensors"]:
    try:
        extra_metadata += copy_metadata(pkg)
    except Exception:
        pass

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
] + model_datas + sl_datas + st_datas + tf_datas + tk_datas + extra_metadata

hiddenimports = [
    "streamlit", "streamlit.web", "streamlit.web.cli",
    "streamlit.web.bootstrap",
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
] + sl_hiddenimports + st_hiddenimports + tf_hiddenimports + tk_hiddenimports

a = Analysis(
    [os.path.join(SRC_DIR, "filesense", "launcher.py")],
    pathex=[SRC_DIR],
    binaries=sl_binaries + st_binaries + tf_binaries + tk_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "matplotlib", "PIL", "cv2",
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
    console=True,  # TODO: set back to False after debugging
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=True,
    name="FileSense",
)
