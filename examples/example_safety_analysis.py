"""
Example usage of the Safe-to-Delete recommendation engine.

This demonstrates how to use the SafetyAnalyzer to identify
files that are likely safe to delete.
"""

from pathlib import Path
from datetime import datetime, timedelta

from src.filesense.core.scanner import FileScanner, FileInfo
from src.filesense.core.analysis import SafetyAnalyzer, DuplicateDetector


def main():
    """Example safety analysis workflow."""
    
    print("=" * 70)
    print("SAFE-TO-DELETE RECOMMENDATION ENGINE - EXAMPLE")
    print("=" * 70)
    print()
    
    # Scan a directory
    documents_path = Path.home() / "Documents"
    
    if not documents_path.exists():
        print(f"Documents folder not found: {documents_path}")
        return
    
    print(f"Scanning: {documents_path}")
    print("This may take a moment...")
    print()
    
    scanner = FileScanner()
    files = scanner.scan_directory(str(documents_path), max_depth=2)
    
    print(f"✓ Found {len(files)} files")
    print()
    
    # Detect duplicates
    print("Detecting duplicates...")
    duplicate_detector = DuplicateDetector()
    
    for file in files:
        duplicate_detector.add_file(file.full_path, file.size_bytes)
    
    duplicate_groups = duplicate_detector.find_duplicates()
    
    # Build duplicate map
    duplicate_map = {}
    for group in duplicate_groups:
        for file_path in group.file_paths:
            duplicate_map[file_path] = len(group.file_paths) - 1
    
    print(f"✓ Found {len(duplicate_groups)} groups of duplicates")
    print()
    
    # Analyze files for safety
    print("Analyzing files for deletion safety...")
    analyzer = SafetyAnalyzer()
    recommendations = analyzer.analyze_batch(files, duplicate_map)
    
    # Get top recommendations (safety score >= 70)
    top_recs = analyzer.get_top_recommendations(
        recommendations,
        min_score=70,
        limit=10
    )
    
    print(f"✓ Generated {len(recommendations)} recommendations")
    print()
    
    # Display top 10 recommendations
    print("=" * 70)
    print("TOP 10 FILES SAFE TO DELETE")
    print("=" * 70)
    print()
    
    for idx, rec in enumerate(top_recs, 1):
        print(f"#{idx}. {rec.file_name}")
        print(f"    Safety Score: {rec.safety_score}% ({rec.risk_level} risk)")
        print(f"    Path: {rec.file_path}")
        print(f"    Size: {rec.size_bytes / 1024:.2f} KB")
        print(f"    Last Accessed: {rec.last_accessed.strftime('%Y-%m-%d')}")
        print(f"    Reasons:")
        for reason in rec.reasons:
            print(f"      • {reason}")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_safe_size = sum(r.size_bytes for r in top_recs)
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for r in recommendations:
        risk_counts[r.risk_level] += 1
    
    print(f"Total files analyzed: {len(recommendations)}")
    print(f"High safety files (70%+): {len(top_recs)}")
    print(f"Potential space to recover: {total_safe_size / (1024 * 1024):.2f} MB")
    print()
    print(f"Risk distribution:")
    print(f"  LOW risk:    {risk_counts['LOW']} files")
    print(f"  MEDIUM risk: {risk_counts['MEDIUM']} files")
    print(f"  HIGH risk:   {risk_counts['HIGH']} files")
    print()
    
    print("=" * 70)
    print("IMPORTANT: Always review files manually before deleting!")
    print("=" * 70)


if __name__ == "__main__":
    main()
