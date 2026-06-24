"""Example: scan files and generate safe-to-delete recommendations."""

from pathlib import Path
from src.filesense.core.scanner import FileScanner
from src.filesense.core.analysis import SafetyAnalyzer, DuplicateDetector


def main():
    documents_path = Path.home() / "Documents"

    if not documents_path.exists():
        print(f"Documents folder not found: {documents_path}")
        return

    print(f"Scanning: {documents_path}")
    scanner = FileScanner()
    files = scanner.scan_directory(str(documents_path), max_depth=2)
    print(f"✓ Found {len(files)} files\n")

    print("Detecting duplicates...")
    duplicate_detector = DuplicateDetector()
    for file in files:
        duplicate_detector.add_file(file.full_path, file.size_bytes)

    duplicate_groups = duplicate_detector.find_duplicates()
    duplicate_map = {}
    for group in duplicate_groups:
        for file_path in group.file_paths:
            duplicate_map[file_path] = len(group.file_paths) - 1
    print(f"✓ Found {len(duplicate_groups)} groups of duplicates\n")

    print("Analyzing files for deletion safety...")
    analyzer = SafetyAnalyzer()
    recommendations = analyzer.analyze_batch(files, duplicate_map)
    top_recs = analyzer.get_top_recommendations(recommendations, min_score=70, limit=10)
    print(f"✓ Generated {len(recommendations)} recommendations\n")

    print("=" * 70)
    print("TOP 10 FILES SAFE TO DELETE")
    print("=" * 70 + "\n")

    for idx, rec in enumerate(top_recs, 1):
        print(f"#{idx}. {rec.file_name}")
        print(f"    Safety Score: {rec.safety_score}% ({rec.risk_level} risk)")
        print(f"    Path: {rec.file_path}")
        print(f"    Size: {rec.size_bytes / 1024:.2f} KB")
        print(f"    Last Accessed: {rec.last_accessed:%Y-%m-%d}")
        print(f"    Reasons:")
        for reason in rec.reasons:
            print(f"      • {reason}")
        print()

    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for r in recommendations:
        risk_counts[r.risk_level] += 1

    print("=" * 70)
    print(f"Total files analyzed: {len(recommendations)}")
    print(f"High safety files (70%+): {len(top_recs)}")
    print(f"Potential space: {sum(r.size_bytes for r in top_recs) / (1024 * 1024):.2f} MB")
    print(f"Risk: LOW={risk_counts['LOW']}  MEDIUM={risk_counts['MEDIUM']}  HIGH={risk_counts['HIGH']}")
    print("=" * 70)
    print("IMPORTANT: Always review files manually before deleting!")


if __name__ == "__main__":
    main()
