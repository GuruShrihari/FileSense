"""
Safe-to-delete recommendation engine.

This module provides rule-based scoring to identify files that are
likely safe to delete, with human-readable explanations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional
import logging

from filesense.core.scanner import FileInfo


logger = logging.getLogger(__name__)


@dataclass
class SafetyRecommendation:
    """
    Safe-to-delete recommendation for a file.
    
    Attributes:
        file_path: Full path to the file
        safety_score: Score from 0-100 (higher = safer to delete)
        reasons: List of human-readable reasons for the score
        risk_level: LOW, MEDIUM, or HIGH
    """
    file_path: str
    file_name: str
    safety_score: int
    reasons: List[str]
    risk_level: str
    size_bytes: int
    last_accessed: datetime
    
    def __repr__(self) -> str:
        return f"SafetyRecommendation(score={self.safety_score}, risk={self.risk_level})"


class SafetyAnalyzer:
    """
    Rule-based file deletion safety analyzer.
    
    Uses transparent, explainable rules to score files based on:
    - Last accessed time (older = safer)
    - File type (temp files, caches = safer)
    - File size (larger = less safe)
    - Duplicate existence (has duplicates = safer)
    
    NO machine learning - all decisions are rule-based and explainable.
    """
    
    # File extensions that are typically safe to delete
    TEMP_FILE_EXTENSIONS = {
        ".tmp", ".temp", ".cache", ".bak", ".old", ".~",
        ".crdownload", ".part", ".partial"
    }
    
    # Cache and temporary directories
    TEMP_DIRECTORY_PATTERNS = {
        "temp", "tmp", "cache", "thumbnails", "backup"
    }
    
    # Large file threshold (in bytes) - 100 MB
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024
    
    def __init__(self) -> None:
        """Initialize the safety analyzer."""
        self.now = datetime.now()
    
    def analyze_file(
        self, 
        file_info: FileInfo,
        has_duplicate: bool = False,
        duplicate_count: int = 0
    ) -> SafetyRecommendation:
        # Analyze file and generate safety recommendation with score and reasons
        score = 0
        reasons = []
        
        # FACTOR 1: Last accessed time (0-40 points)
        time_score, time_reason = self._score_access_time(file_info.last_accessed)
        score += time_score
        if time_reason:
            reasons.append(time_reason)
        
        # FACTOR 2: File type (0-30 points)
        type_score, type_reason = self._score_file_type(file_info)
        score += type_score
        if type_reason:
            reasons.append(type_reason)
        
        # FACTOR 3: File size (0-15 points)
        size_score, size_reason = self._score_file_size(file_info.size_bytes)
        score += size_score
        if size_reason:
            reasons.append(size_reason)
        
        # FACTOR 4: Duplicate existence (0-15 points)
        dup_score, dup_reason = self._score_duplicates(has_duplicate, duplicate_count)
        score += dup_score
        if dup_reason:
            reasons.append(dup_reason)
        
        # Determine risk level based on score
        if score >= 70:
            risk_level = "LOW"
        elif score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        return SafetyRecommendation(
            file_path=file_info.full_path,
            file_name=file_info.name,
            safety_score=min(100, score),  # Cap at 100
            reasons=reasons,
            risk_level=risk_level,
            size_bytes=file_info.size_bytes,
            last_accessed=file_info.last_accessed
        )
    
    def _score_access_time(self, last_accessed: datetime) -> Tuple[int, Optional[str]]:
        # Score based on days since last access (older = higher score)
        days_since_access = (self.now - last_accessed).days
        
        if days_since_access > 730:  # 2+ years
            return (40, f"Not accessed in {days_since_access // 365} years")
        elif days_since_access > 365:  # 1+ year
            return (35, f"Not accessed in {days_since_access // 30} months")
        elif days_since_access > 180:  # 6+ months
            return (25, f"Not accessed in {days_since_access // 30} months")
        elif days_since_access > 90:  # 3+ months
            return (15, f"Not accessed in {days_since_access} days")
        elif days_since_access > 30:  # 1+ month
            return (10, f"Not accessed in {days_since_access} days")
        elif days_since_access > 7:  # 1+ week
            return (5, None)
        else:
            return (0, "Recently accessed")
    
    def _score_file_type(self, file_info: FileInfo) -> Tuple[int, Optional[str]]:
        # Score based on file type and location (temp/backup/log files)
        extension = file_info.extension.lower()
        path = Path(file_info.full_path)
        
        # Check if it's a temporary file
        if extension in self.TEMP_FILE_EXTENSIONS:
            return (30, "Temporary file type")
        
        # Check if it's in a temp directory
        path_lower = str(path.parent).lower()
        for pattern in self.TEMP_DIRECTORY_PATTERNS:
            if pattern in path_lower:
                return (25, f"In {pattern} directory")
        
        # Check for backup files
        if "backup" in file_info.name.lower() or extension in {".bak", ".old"}:
            return (20, "Backup file")
        
        # Check for log files
        if extension in {".log", ".txt"} and "log" in file_info.name.lower():
            return (15, "Log file")
        
        # Check for downloads
        if "download" in path_lower:
            return (10, "In downloads folder")
        
        return (0, None)
    
    def _score_file_size(self, size_bytes: int) -> Tuple[int, Optional[str]]:
        # Score based on file size (smaller = safer to delete)
        if size_bytes < 1024:  # < 1 KB
            return (15, "Very small file")
        elif size_bytes < 10 * 1024:  # < 10 KB
            return (12, "Small file")
        elif size_bytes < 100 * 1024:  # < 100 KB
            return (10, None)
        elif size_bytes < 1024 * 1024:  # < 1 MB
            return (7, None)
        elif size_bytes < 10 * 1024 * 1024:  # < 10 MB
            return (5, None)
        elif size_bytes < self.LARGE_FILE_THRESHOLD:  # < 100 MB
            return (3, None)
        else:
            return (0, f"Large file ({size_bytes // (1024 * 1024)} MB)")
    
    def _score_duplicates(self, has_duplicate: bool, duplicate_count: int) -> Tuple[int, Optional[str]]:
        # Score based on duplicate count (more duplicates = safer)
        if not has_duplicate:
            return (0, None)
        
        if duplicate_count >= 3:
            return (15, f"{duplicate_count} duplicates exist")
        elif duplicate_count >= 2:
            return (12, f"{duplicate_count} duplicates exist")
        else:
            return (10, "Duplicate exists")
    
    def analyze_batch(
        self, 
        files: List[FileInfo],
        duplicate_map: Optional[dict] = None
    ) -> List[SafetyRecommendation]:
        # Analyze multiple files and return sorted recommendations
        recommendations = []
        
        for file_info in files:
            has_dup = False
            dup_count = 0
            
            if duplicate_map and file_info.full_path in duplicate_map:
                has_dup = True
                dup_count = duplicate_map[file_info.full_path]
            
            recommendation = self.analyze_file(file_info, has_dup, dup_count)
            recommendations.append(recommendation)
        
        # Sort by safety score (highest first)
        recommendations.sort(key=lambda r: r.safety_score, reverse=True)
        
        return recommendations
    
    def get_top_recommendations(
        self,
        recommendations: List[SafetyRecommendation],
        min_score: int = 50,
        limit: int = 50
    ) -> List[SafetyRecommendation]:
        # Get top recommendations filtered by minimum score
        filtered = [r for r in recommendations if r.safety_score >= min_score]
        return filtered[:limit]
