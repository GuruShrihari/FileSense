# FileSense

A Windows-based, Python-powered local file management application.

## 🎯 Overview

FileSense is a Windows-only, offline-first application for local file management and organization.

## 📋 Requirements

- **OS**: Windows 10/11
- **Python**: 3.10+
- **Dependencies**: See `requirements.txt`

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m filesense
```

## 🛠️ Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## 📁 Project Structure

```
FileSense/
├── src/filesense/      # Main application package
│   ├── core/           # Core business logic
│   ├── ui/             # User interface components
│   ├── utils/          # Helper utilities
│   └── config/         # Configuration management
├── tests/              # Test suite
├── data/               # Runtime data (gitignored)
└── docs/               # Documentation
```

## 📝 Status

**Version**: 0.1.0  
**Status**: Bootstrap / Initial Setup

## 📄 License

TBD

## 👤 Author

Shrihari Gururajan
