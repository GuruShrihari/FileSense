"""
Directory and file filtering logic.

This module contains functions to determine which directories and files
should be skipped during filesystem scanning on Windows.
"""

from pathlib import Path
from typing import Set


# System directories that should be skipped for safety and performance
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

# Hidden/system folder patterns to skip
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
    """
    Determine if a directory should be skipped during scanning.

    Skips:
    - Windows system directories (C:\\Windows, Program Files, etc.)
    - AppData folders
    - Hidden system folders
    - Common development folders (node_modules, .git, etc.)

    Args:
        path: Directory path to check

    Returns:
        True if the directory should be skipped, False otherwise

    Examples:
        >>> should_skip_directory(Path("C:/Windows"))
        True
        >>> should_skip_directory(Path("C:/Users/John/Documents"))
        False
    """
    try:
        # Get the lowercase name for case-insensitive comparison
        dir_name_lower = path.name.lower()

        # Check if it's a system folder by name
        if dir_name_lower in SYSTEM_FOLDERS:
            return True

        # Check if path contains any skip patterns (e.g., AppData anywhere)
        path_parts_lower = {part.lower() for part in path.parts}
        if path_parts_lower & SKIP_PATTERNS:
            return True

        # Skip if it's on C: drive and in root-level system folders
        if len(path.parts) >= 2:
            drive = path.parts[0].lower()
            root_folder = path.parts[1].lower()

            # C:\Windows, C:\Program Files, etc.
            if drive in ("c:", "c:\\") and root_folder in SYSTEM_FOLDERS:
                return True

        # Skip hidden directories (starting with .)
        if path.name.startswith(".") and path.name not in (".", ".."):
            return True

        return False

    except (OSError, ValueError):
        # If we can't determine, skip it for safety
        return True


def is_valid_file(path: Path) -> bool:
    """
    Check if a file should be included in the scan results.

    Args:
        path: File path to check

    Returns:
        True if the file should be included, False otherwise
    """
    try:
        # Skip hidden files
        if path.name.startswith("."):
            return False

        # Skip system files
        if path.name.startswith("$"):
            return False

        # File must exist and be a regular file
        if not path.is_file():
            return False

        return True

    except (OSError, ValueError):
        return False
