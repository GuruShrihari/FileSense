"""Directory and file filtering for filesystem scanning."""

from pathlib import Path
from typing import Set

SYSTEM_FOLDERS: Set[str] = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "$recycle.bin",
    "system volume information",
    "$windows.~bt",
    "$windows.~ws",
    "recovery",
}

SKIP_PATTERNS: Set[str] = {
    "appdata",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".cache",
}


def should_skip_directory(path: Path) -> bool:
    """Return True if the directory should be excluded from scanning."""
    try:
        dir_name_lower = path.name.lower()

        if dir_name_lower in SYSTEM_FOLDERS:
            return True

        path_parts_lower = {part.lower() for part in path.parts}
        if path_parts_lower & SKIP_PATTERNS:
            return True

        if len(path.parts) >= 2:
            drive = path.parts[0].lower()
            root_folder = path.parts[1].lower()
            if drive in ("c:", "c:\\") and root_folder in SYSTEM_FOLDERS:
                return True

        if path.name.startswith(".") and path.name not in (".", ".."):
            return True

        return False

    except (OSError, ValueError):
        return True


def is_valid_file(path: Path) -> bool:
    """Return True if the file should be included in scan results."""
    try:
        if path.name.startswith("."):
            return False
        if path.name.startswith("$"):
            return False
        if not path.is_file():
            return False
        return True
    except (OSError, ValueError):
        return False
