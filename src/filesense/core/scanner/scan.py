"""Filesystem scanning with system folder filtering and permission handling."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from .filters import should_skip_directory, is_valid_file

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Container for file metadata."""

    full_path: str
    name: str
    extension: str
    size_bytes: int
    last_accessed: datetime

    def __repr__(self) -> str:
        size_kb = self.size_bytes / 1024
        return (
            f"FileInfo(name='{self.name}', "
            f"size={size_kb:.2f}KB, "
            f"ext='{self.extension}')"
        )


class FileScanner:
    """Recursive filesystem scanner with safety filters."""

    def __init__(self) -> None:
        self.files_scanned: int = 0
        self.errors_encountered: int = 0
        self.directories_skipped: int = 0

    def scan_directory(
        self, root_path: str, recursive: bool = True, max_depth: Optional[int] = None
    ) -> List[FileInfo]:
        """Scan directory and return metadata for all accessible files."""
        root = Path(root_path).resolve()

        if not root.exists():
            raise ValueError(f"Path does not exist: {root_path}")
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root_path}")

        self.files_scanned = 0
        self.errors_encountered = 0
        self.directories_skipped = 0

        logger.info(f"Starting scan of: {root}")

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
        if max_depth is not None and current_depth > max_depth:
            return

        if should_skip_directory(directory):
            self.directories_skipped += 1
            logger.debug(f"Skipping system directory: {directory}")
            return

        try:
            for item in directory.iterdir():
                try:
                    if item.is_dir():
                        self._scan_recursive(
                            item, results, current_depth + 1, max_depth
                        )
                    elif item.is_file():
                        if is_valid_file(item):
                            file_info = self._extract_file_info(item)
                            if file_info:
                                results.append(file_info)
                                self.files_scanned += 1

                except PermissionError:
                    self.errors_encountered += 1
                    logger.warning(f"Permission denied: {item}")

                except OSError as e:
                    self.errors_encountered += 1
                    logger.warning(f"OS error accessing {item}: {e}")

        except PermissionError:
            self.errors_encountered += 1
            logger.warning(f"Permission denied for directory: {directory}")

        except OSError as e:
            self.errors_encountered += 1
            logger.warning(f"OS error scanning directory {directory}: {e}")

    def _extract_file_info(self, file_path: Path) -> Optional[FileInfo]:
        try:
            stats = file_path.stat()
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
        return {
            "files_scanned": self.files_scanned,
            "errors_encountered": self.errors_encountered,
            "directories_skipped": self.directories_skipped,
        }
