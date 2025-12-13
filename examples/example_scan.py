"""
Example usage of the FileScanner.

This demonstrates how to use the filesystem scanner to
list files in a directory.
"""

from pathlib import Path
from src.filesense.core.scanner import FileScanner


def main():
    """Example scanning workflow."""
    
    # Create scanner instance
    scanner = FileScanner()
    
    # Example 1: Scan user's Documents folder
    print("=" * 60)
    print("EXAMPLE 1: Scanning Documents folder")
    print("=" * 60)
    
    documents_path = Path.home() / "Documents"
    
    if documents_path.exists():
        # Scan with depth limit for safety
        files = scanner.scan_directory(
            root_path=str(documents_path),
            recursive=True,
            max_depth=3  # Only go 3 levels deep
        )
        
        # Display results
        print(f"\nFound {len(files)} files\n")
        
        # Show first 10 files
        for file_info in files[:10]:
            size_kb = file_info.size_bytes / 1024
            print(f"📄 {file_info.name}")
            print(f"   Path: {file_info.full_path}")
            print(f"   Size: {size_kb:.2f} KB")
            print(f"   Type: {file_info.extension or 'No extension'}")
            print(f"   Last accessed: {file_info.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        if len(files) > 10:
            print(f"... and {len(files) - 10} more files")
        
        # Show statistics
        stats = scanner.get_stats()
        print(f"\n📊 Scan Statistics:")
        print(f"   Files scanned: {stats['files_scanned']}")
        print(f"   Directories skipped: {stats['directories_skipped']}")
        print(f"   Errors encountered: {stats['errors_encountered']}")
    
    else:
        print(f"Documents folder not found: {documents_path}")
    
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Scan specific folder")
    print("=" * 60)
    
    # Example 2: Scan a specific folder (change this to test)
    test_folder = Path.home() / "Desktop"
    
    if test_folder.exists():
        files = scanner.scan_directory(str(test_folder), recursive=False)
        print(f"\nFound {len(files)} files in Desktop (non-recursive)\n")
        
        # Group by extension
        extensions = {}
        for file in files:
            ext = file.extension or "no_extension"
            extensions[ext] = extensions.get(ext, 0) + 1
        
        print("Files by type:")
        for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
            print(f"   {ext}: {count} files")
    else:
        print(f"Desktop folder not found: {test_folder}")


if __name__ == "__main__":
    main()
