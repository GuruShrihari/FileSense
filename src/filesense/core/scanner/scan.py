"""
Main filesystem scanning functionality.

This module provides the FileScanner class for traversing directories
and collecting file metadata on Windows systems.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from .filters import should_skip_directory, is_valid_file


# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """
    Container for file metadata.

    Attributes:
        full_path: Complete absolute path to the file
        name: File name without directory path
        extension: File extension (e.g., '.txt', '.pdf')
        size_bytes: File size in bytes
        last_accessed: Last access timestamp
    """

    full_path: str
    name: str
    extension: str
    size_bytes: int
    last_accessed: datetime

    def __repr__(self) -> str:
        """Human-readable representation."""
        size_kb = self.size_bytes / 1024
        return (
            f"FileInfo(name='{self.name}', "
            f"size={size_kb:.2f}KB, "
            f"ext='{self.extension}')"
        )


class FileScanner:
    """
    Filesystem scanner for Windows directories.

    Scans directories recursively while respecting system folder filters
    and handling permission errors gracefully.

    Example:
        >>> scanner = FileScanner()
        >>> files = scanner.scan_directory("C:/Users/John/Documents")
        >>> print(f"Found {len(files)} files")
    """

    def __init__(self) -> None:
        """Initialize the FileScanner."""
        self.files_scanned: int = 0
        self.errors_encountered: int = 0
        self.directories_skipped: int = 0

    def scan_directory(
        self, root_path: str, recursive: bool = True, max_depth: Optional[int] = None
    ) -> List[FileInfo]:
        """
        Scan a directory and return metadata for all accessible files.

        Args:
            root_path: Starting directory path (as string)
            recursive: Whether to scan subdirectories (default: True)
            max_depth: Maximum recursion depth (None = unlimited)

        Returns:
            List of FileInfo objects for all discovered files

        Raises:
            ValueError: If root_path doesn't exist or isn't a directory
        """
        # Convert to Path object
        root = Path(root_path).resolve()

        # Validate root path
        if not root.exists():
            raise ValueError(f"Path does not exist: {root_path}")

        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root_path}")

        # Reset counters
        self.files_scanned = 0
        self.errors_encountered = 0
        self.directories_skipped = 0

        logger.info(f"Starting scan of: {root}")

        # Collect all files
        files: List[FileInfo] = []
        self._scan_recursive(root, files, current_depth=0, max_depth=max_depth)

        logger.info(
            f"Scan complete. Files: {self.files_scanned}, "
            f"Errors: {self.errors_encountered}, "
            f"Skipped dirs: {self.directories_skipped}"
        )

        return files

    def _scan_recursive(
        self,
        directory: Path,
        results: List[FileInfo],
        current_depth: int,
        max_depth: Optional[int],
    ) -> None:
        """
        Internal recursive scanning method.

        Args:
            directory: Current directory to scan
            results: List to append FileInfo objects to
            current_depth: Current recursion depth
            max_depth: Maximum allowed depth (None = unlimited)
        """
        # Check depth limit
        if max_depth is not None and current_depth > max_depth:
            return

        # Check if we should skip this directory
        if should_skip_directory(directory):
            self.directories_skipped += 1
            logger.debug(f"Skipping system directory: {directory}")
            return

        try:
            # Iterate through directory contents
            for item in directory.iterdir():
                try:
                    # Handle subdirectories
                    if item.is_dir():
                        self._scan_recursive(
                            item, results, current_depth + 1, max_depth
                        )

                    # Handle files
                    elif item.is_file():
                        if is_valid_file(item):
                            file_info = self._extract_file_info(item)
                            if file_info:
                                results.append(file_info)
                                self.files_scanned += 1

                except PermissionError:
                    # Gracefully handle permission denied errors
                    self.errors_encountered += 1
                    logger.warning(f"Permission denied: {item}")

                except OSError as e:
                    # Handle other OS errors (file locked, etc.)
                    self.errors_encountered += 1
                    logger.warning(f"OS error accessing {item}: {e}")

        except PermissionError:
            self.errors_encountered += 1
            logger.warning(f"Permission denied for directory: {directory}")

        except OSError as e:
            self.errors_encountered += 1
            logger.warning(f"OS error scanning directory {directory}: {e}")

    def _extract_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """
        Extract metadata from a file.

        Args:
            file_path: Path to the file

        Returns:
            FileInfo object, or None if extraction fails
        """
        try:
            # Get file stats
            stats = file_path.stat()

            # Create FileInfo object
            return FileInfo(
                full_path=str(file_path.resolve()),
                name=file_path.name,
                extension=file_path.suffix.lower(),
                size_bytes=stats.st_size,
                last_accessed=datetime.fromtimestamp(stats.st_atime),
            )

        except (OSError, ValueError) as e:
            logger.warning(f"Failed to extract info from {file_path}: {e}")
            return None

    def get_stats(self) -> dict:
        """
        Get scanning statistics from the last scan.

        Returns:
            Dictionary with scan statistics
        """
        return {
            "files_scanned": self.files_scanned,
            "errors_encountered": self.errors_encountered,
            "directories_skipped": self.directories_skipped,
        }
