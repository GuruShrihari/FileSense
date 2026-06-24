"""Rule-based safe-to-delete recommendation engine."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import logging

from filesense.core.scanner import FileInfo

logger = logging.getLogger(__name__)


@dataclass
class SafetyRecommendation:
    """Safe-to-delete recommendation with score, reasons, and risk level."""
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
    """Scores files for deletion safety using transparent, rule-based heuristics."""

    TEMP_FILE_EXTENSIONS = {
        ".tmp", ".temp", ".cache", ".bak", ".old", ".~",
        ".crdownload", ".part", ".partial"
    }
    TEMP_DIRECTORY_PATTERNS = {"temp", "tmp", "cache", "thumbnails", "backup"}
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024

    def __init__(self) -> None:
        self.now = datetime.now()

    def analyze_file(self, file_info: FileInfo, has_duplicate: bool = False, duplicate_count: int = 0) -> SafetyRecommendation:
        score = 0
        reasons = []
        for fn, args in [
            (self._score_access_time, (file_info.last_accessed,)),
            (self._score_file_type, (file_info,)),
            (self._score_file_size, (file_info.size_bytes,)),
            (self._score_duplicates, (has_duplicate, duplicate_count)),
        ]:
            s, r = fn(*args)
            score += s
            if r:
                reasons.append(r)

        risk_level = "LOW" if score >= 70 else "MEDIUM" if score >= 40 else "HIGH"
        return SafetyRecommendation(
            file_path=file_info.full_path, file_name=file_info.name,
            safety_score=min(100, score), reasons=reasons, risk_level=risk_level,
            size_bytes=file_info.size_bytes, last_accessed=file_info.last_accessed,
        )

    def _score_access_time(self, last_accessed: datetime) -> Tuple[int, Optional[str]]:
        days = (self.now - last_accessed).days
        if days > 730:
            return (40, f"Not accessed in {days // 365} years")
        elif days > 365:
            return (35, f"Not accessed in {days // 30} months")
        elif days > 180:
            return (25, f"Not accessed in {days // 30} months")
        elif days > 90:
            return (15, f"Not accessed in {days} days")
        elif days > 30:
            return (10, f"Not accessed in {days} days")
        elif days > 7:
            return (5, None)
        return (0, "Recently accessed")

    def _score_file_type(self, file_info: FileInfo) -> Tuple[int, Optional[str]]:
        ext = file_info.extension.lower()
        if ext in self.TEMP_FILE_EXTENSIONS:
            return (30, "Temporary file type")
        path_lower = str(Path(file_info.full_path).parent).lower()
        for pattern in self.TEMP_DIRECTORY_PATTERNS:
            if pattern in path_lower:
                return (25, f"In {pattern} directory")
        if "backup" in file_info.name.lower() or ext in {".bak", ".old"}:
            return (20, "Backup file")
        if ext in {".log", ".txt"} and "log" in file_info.name.lower():
            return (15, "Log file")
        if "download" in path_lower:
            return (10, "In downloads folder")
        return (0, None)

    def _score_file_size(self, size_bytes: int) -> Tuple[int, Optional[str]]:
        if size_bytes < 1024:
            return (15, "Very small file")
        elif size_bytes < 10 * 1024:
            return (12, "Small file")
        elif size_bytes < 100 * 1024:
            return (10, None)
        elif size_bytes < 1024 * 1024:
            return (7, None)
        elif size_bytes < 10 * 1024 * 1024:
            return (5, None)
        elif size_bytes < self.LARGE_FILE_THRESHOLD:
            return (3, None)
        return (0, f"Large file ({size_bytes // (1024 * 1024)} MB)")

    def _score_duplicates(self, has_duplicate: bool, count: int) -> Tuple[int, Optional[str]]:
        if not has_duplicate:
            return (0, None)
        if count >= 3:
            return (15, f"{count} duplicates exist")
        elif count >= 2:
            return (12, f"{count} duplicates exist")
        return (10, "Duplicate exists")

    def analyze_batch(self, files: List[FileInfo], duplicate_map: Optional[dict] = None) -> List[SafetyRecommendation]:
        recs = []
        for f in files:
            has_dup = bool(duplicate_map and f.full_path in duplicate_map)
            dup_count = duplicate_map.get(f.full_path, 0) if duplicate_map else 0
            recs.append(self.analyze_file(f, has_dup, dup_count))
        recs.sort(key=lambda r: r.safety_score, reverse=True)
        return recs

    def get_top_recommendations(self, recommendations: List[SafetyRecommendation], min_score: int = 50, limit: int = 50) -> List[SafetyRecommendation]:
        return [r for r in recommendations if r.safety_score >= min_score][:limit]
