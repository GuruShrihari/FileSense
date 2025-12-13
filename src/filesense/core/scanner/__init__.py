"""
Filesystem scanner module.

This module provides functionality for scanning and indexing files
on the Windows filesystem with appropriate safety filters.
"""

from .scan import FileScanner, FileInfo
from .filters import should_skip_directory

__all__ = ["FileScanner", "FileInfo", "should_skip_directory"]
