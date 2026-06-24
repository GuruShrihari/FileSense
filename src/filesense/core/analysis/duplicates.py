"""Duplicate file detection using SHA-256 content hashing."""

import hashlib
from typing import Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """Group of files with identical content."""
    file_hash: str
    file_paths: List[str]
    size_bytes: int

    def __repr__(self) -> str:
        return f"DuplicateGroup(count={len(self.file_paths)}, size={self.size_bytes})"


class DuplicateDetector:
    """Detect duplicate files by grouping by size, then comparing SHA-256 hashes."""

    def __init__(self) -> None:
        self.hash_map: Dict[str, List[str]] = {}
        self.size_map: Dict[int, List[str]] = {}
        self.files_processed = 0
        self.duplicates_found = 0

    def add_file(self, file_path: str, size_bytes: int) -> None:
        if size_bytes not in self.size_map:
            self.size_map[size_bytes] = []
        self.size_map[size_bytes].append(file_path)
        self.files_processed += 1

    def compute_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not hash file {file_path}: {e}")
            return ""

    def find_duplicates(self) -> List[DuplicateGroup]:
        """Find all groups of files with identical content."""
        duplicate_groups = []

        for size_bytes, file_paths in self.size_map.items():
            if len(file_paths) < 2:
                continue

            hash_to_paths: Dict[str, List[str]] = {}
            for fp in file_paths:
                fh = self.compute_hash(fp)
                if fh:
                    hash_to_paths.setdefault(fh, []).append(fp)

            for file_hash, paths in hash_to_paths.items():
                if len(paths) > 1:
                    duplicate_groups.append(
                        DuplicateGroup(file_hash=file_hash, file_paths=paths, size_bytes=size_bytes)
                    )
                    self.duplicates_found += len(paths) - 1

        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups

    def is_duplicate(self, file_path: str) -> bool:
        file_hash = self.compute_hash(file_path)
        return bool(file_hash and file_hash in self.hash_map and len(self.hash_map[file_hash]) > 1)

    def get_duplicates_of(self, file_path: str) -> List[str]:
        file_hash = self.compute_hash(file_path)
        if not file_hash or file_hash not in self.hash_map:
            return []
        return [p for p in self.hash_map[file_hash] if p != file_path]

    def get_stats(self) -> dict:
        return {
            "files_processed": self.files_processed,
            "duplicates_found": self.duplicates_found,
            "duplicate_groups": len([h for h, paths in self.hash_map.items() if len(paths) > 1])
        }
