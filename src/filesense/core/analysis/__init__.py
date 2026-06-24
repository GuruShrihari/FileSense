"""File analysis: safety scoring and duplicate detection."""

from .safety_score import SafetyAnalyzer, SafetyRecommendation
from .duplicates import DuplicateDetector

__all__ = ["SafetyAnalyzer", "SafetyRecommendation", "DuplicateDetector"]
