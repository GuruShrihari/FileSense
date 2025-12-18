"""
Duplicate file detection.

This module identifies duplicate files based on content hash (SHA-256)
and file metadata for safe deletion recommendations.
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """
    Group of duplicate files.
    
    Attributes:
        file_hash: SHA-256 hash of the file content
        file_paths: List of paths to duplicate files
        size_bytes: Size of each file in bytes
    """
    file_hash: str
    file_paths: List[str]
    size_bytes: int
    
    def __repr__(self) -> str:
        return f"DuplicateGroup(count={len(self.file_paths)}, size={self.size_bytes})"


class DuplicateDetector:
    """
    Detect duplicate files based on content hash.
    
    Uses SHA-256 hashing to identify files with identical content.
    This is more reliable than just comparing file names or sizes.
    """
    
    def __init__(self) -> None:
        """Initialize the duplicate detector."""
        self.hash_map: Dict[str, List[str]] = {}
        self.size_map: Dict[int, List[str]] = {}
        self.files_processed = 0
        self.duplicates_found = 0
    
    def add_file(self, file_path: str, size_bytes: int) -> None:
        # Add file to duplicate tracking by grouping by size first
        # Group by size first (optimization - only hash files with same size)
        if size_bytes not in self.size_map:
            self.size_map[size_bytes] = []
        self.size_map[size_bytes].append(file_path)
        self.files_processed += 1
    
    def compute_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        # Compute SHA-256 hash of file content in chunks
        sha256 = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    sha256.update(chunk)
            
            return sha256.hexdigest()
        
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not hash file {file_path}: {e}")
            return ""
    
    def find_duplicates(self) -> List[DuplicateGroup]:
        # Find all duplicate files by comparing SHA-256 hashes
        duplicate_groups = []
        
        # Only process files that have at least one other file with same size
        for size_bytes, file_paths in self.size_map.items():
            if len(file_paths) < 2:
                continue  # No duplicates possible if only one file of this size
            
            # Hash all files with this size
            hash_to_paths: Dict[str, List[str]] = {}
            
            for file_path in file_paths:
                file_hash = self.compute_hash(file_path)
                if file_hash:
                    if file_hash not in hash_to_paths:
                        hash_to_paths[file_hash] = []
                    hash_to_paths[file_hash].append(file_path)
            
            # Collect groups where hash appears multiple times
            for file_hash, paths in hash_to_paths.items():
                if len(paths) > 1:
                    duplicate_groups.append(
                        DuplicateGroup(
                            file_hash=file_hash,
                            file_paths=paths,
                            size_bytes=size_bytes
                        )
                    )
                    self.duplicates_found += len(paths) - 1  # Count extras
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    def is_duplicate(self, file_path: str) -> bool:
        # Check if a file has at least one duplicate
        file_hash = self.compute_hash(file_path)
        if not file_hash:
            return False
        
        return file_hash in self.hash_map and len(self.hash_map[file_hash]) > 1
    
    def get_duplicates_of(self, file_path: str) -> List[str]:
        # Get all duplicates of a specific file (excluding itself)
        file_hash = self.compute_hash(file_path)
        if not file_hash or file_hash not in self.hash_map:
            return []
        
        duplicates = self.hash_map[file_hash].copy()
        if file_path in duplicates:
            duplicates.remove(file_path)
        
        return duplicates
    
    def get_stats(self) -> dict:
        # Get duplicate detection statistics
        return {
            "files_processed": self.files_processed,
            "duplicates_found": self.duplicates_found,
            "duplicate_groups": len([h for h, paths in self.hash_map.items() if len(paths) > 1])
        }
