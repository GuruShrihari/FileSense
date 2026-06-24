# FileSense

A Windows-based, Python-powered local file management desktop application.

## Overview

FileSense is an offline-first desktop application for local file management and organization. It launches as a native window — no browser tabs, no localhost URLs.

### Features
- **File Scanner** — Recursive directory scanning with system folder filtering
- **Semantic Search** — Find files by meaning using sentence-transformers + FAISS
- **Safe-to-Delete** — Rule-based, explainable recommendations for cleanup
- **Duplicate Detection** — SHA-256 content hashing to find identical files

## Requirements

- **OS**: Windows 10/11
- **Python**: 3.11+
- **Dependencies**: See `requirements.txt`

## Quick Start

```bash
pip install -r requirements.txt
python -m filesense
```

A native desktop window titled **FileSense** will open with the full UI inside.

## Building the .exe

```bash
# One-click build (Windows)
build_exe.bat

# Or manually:
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
pyinstaller filesense.spec --noconfirm
```

Output: `dist/FileSense/FileSense.exe`

Distribute the entire `dist/FileSense/` folder as a zip.

## Project Structure

```
FileSense/
├── src/filesense/
│   ├── launcher.py         # Desktop launcher (pywebview + Streamlit)
│   ├── desktop_config.py   # Headless Streamlit configuration
│   ├── ui/app.py           # Streamlit UI
│   └── core/
│       ├── scanner/        # File scanning + filters
│       ├── extractor/      # Text extraction (.txt, .pdf, .docx)
│       ├── embeddings/     # Sentence-transformers + FAISS index
│       └── analysis/       # Safety scoring + duplicate detection
├── examples/               # Usage examples
├── filesense.spec          # PyInstaller build spec
├── build_exe.bat           # One-click Windows build
└── requirements.txt        # Runtime dependencies
```

## Development

```bash
pip install -r requirements-dev.txt
pytest
black src/
mypy src/
```

## Author

Shrihari Gururajan
