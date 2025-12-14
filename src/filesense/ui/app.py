"""
Streamlit UI for FileSense.

A minimal web-based interface for scanning and displaying files
from selected directories.
"""

import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime

from src.filesense.core.scanner import FileScanner


def format_file_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title="FileSense",
        page_icon="📁",
        layout="wide"
    )
    
    # Header
    st.title("📁 FileSense")
    st.markdown("**Windows-based local file scanner**")
    st.markdown("---")
    
    # Sidebar for inputs
    st.sidebar.header("⚙️ Scan Settings")
    
    # Folder path input
    folder_path = st.sidebar.text_input(
        "Folder Path",
        value=str(Path.home() / "Documents"),
        help="Enter the full path to the folder you want to scan"
    )
    
    # Scan options
    recursive = st.sidebar.checkbox(
        "Scan subdirectories",
        value=True,
        help="Include files from subdirectories"
    )
    
    max_depth = st.sidebar.number_input(
        "Max depth",
        min_value=1,
        max_value=10,
        value=3,
        help="Maximum directory depth to scan (prevents deep recursion)"
    )
    
    # Scan button
    scan_button = st.sidebar.button("🔍 Start Scan", type="primary", use_container_width=True)
    
    # Main content area
    if scan_button:
        # Validate path
        target_path = Path(folder_path)
        
        if not target_path.exists():
            st.error(f"❌ Path does not exist: {folder_path}")
            return
        
        if not target_path.is_dir():
            st.error(f"❌ Path is not a directory: {folder_path}")
            return
        
        # Show scanning status
        with st.spinner(f"🔍 Scanning {folder_path}..."):
            try:
                # Create scanner and run scan
                scanner = FileScanner()
                files = scanner.scan_directory(
                    root_path=str(target_path),
                    recursive=recursive,
                    max_depth=max_depth if recursive else None
                )
                
                # Get statistics
                stats = scanner.get_stats()
                
            except Exception as e:
                st.error(f"❌ Error during scan: {str(e)}")
                return
        
        # Display results
        st.success(f"✅ Scan complete! Found {len(files)} files")
        
        # Show statistics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Files Found", stats["files_scanned"])
        
        with col2:
            st.metric("Directories Skipped", stats["directories_skipped"])
        
        with col3:
            st.metric("Errors Encountered", stats["errors_encountered"])
        
        st.markdown("---")
        
        # Display files in a table
        if files:
            st.subheader("📄 Scanned Files")
            
            # Convert FileInfo objects to DataFrame
            data = []
            for file in files:
                data.append({
                    "Name": file.name,
                    "Extension": file.extension or "(none)",
                    "Size": format_file_size(file.size_bytes),
                    "Size (bytes)": file.size_bytes,
                    "Last Accessed": file.last_accessed.strftime("%Y-%m-%d %H:%M:%S"),
                    "Path": file.full_path
                })
            
            df = pd.DataFrame(data)
            
            # Display with filters
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Name": st.column_config.TextColumn("File Name", width="medium"),
                    "Extension": st.column_config.TextColumn("Type", width="small"),
                    "Size": st.column_config.TextColumn("Size", width="small"),
                    "Size (bytes)": None,  # Hide raw bytes column
                    "Last Accessed": st.column_config.TextColumn("Last Accessed", width="medium"),
                    "Path": st.column_config.TextColumn("Full Path", width="large")
                }
            )
            
            # Summary statistics
            st.markdown("---")
            st.subheader("📊 Summary")
            
            # Total size
            total_size = sum(file.size_bytes for file in files)
            st.write(f"**Total size:** {format_file_size(total_size)}")
            
            # File types breakdown
            extensions = {}
            for file in files:
                ext = file.extension or "(no extension)"
                extensions[ext] = extensions.get(ext, 0) + 1
            
            if extensions:
                st.write("**Files by type:**")
                ext_df = pd.DataFrame([
                    {"Extension": ext, "Count": count}
                    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)
                ])
                st.dataframe(ext_df, hide_index=True, use_container_width=True)
        
        else:
            st.warning("⚠️ No files found in the specified directory")
    
    else:
        # Welcome screen
        st.info("👈 Enter a folder path and click **Start Scan** to begin")
        
        st.markdown("""
        ### How to use:
        1. Enter a folder path in the sidebar (or use the default)
        2. Choose whether to scan subdirectories
        3. Set the maximum scan depth
        4. Click **Start Scan**
        
        ### Safety features:
        - System folders are automatically skipped (Windows, Program Files, etc.)
        - Permission errors are handled gracefully
        - Depth limiting prevents infinite recursion
        """)


if __name__ == "__main__":
    main()
