"""
Streamlit UI for FileSense.

A minimal web-based interface for scanning and displaying files
from selected directories with semantic search capabilities.
"""


import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime
import logging
import sys

# Resolve the src/ directory for imports.
# Handles both normal execution and PyInstaller frozen bundles.
if getattr(sys, "frozen", False):
    # Inside a PyInstaller bundle: _MEIPASS is the temp extraction root
    _BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BASE = Path(__file__).resolve().parents[2]

if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from filesense.core.scanner import FileScanner
from filesense.core.extractor import TextExtractor
from filesense.core.embeddings import EmbeddingModel, VectorIndex
from filesense.core.analysis import SafetyAnalyzer, DuplicateDetector


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    # Convert bytes to human-readable format (KB, MB, GB, etc.)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def main():
    # Main Streamlit application entry point
    
    # Page configuration
    st.set_page_config(
        page_title="FileSense",
        page_icon="📁",
        layout="wide"
    )
    
    # Initialize session state
    if "files" not in st.session_state:
        st.session_state.files = None
    if "index" not in st.session_state:
        st.session_state.index = None
    if "embedding_model" not in st.session_state:
        st.session_state.embedding_model = None
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None
    if "duplicate_detector" not in st.session_state:
        st.session_state.duplicate_detector = None
    
    # Header
    st.title("📁 FileSense")
    st.markdown("**Windows-based local file scanner with semantic search**")
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
    
    # Indexing options
    st.sidebar.markdown("---")
    st.sidebar.header("🧠 Semantic Search")
    enable_indexing = st.sidebar.checkbox(
        "Build search index",
        value=True,
        help="Extract text and build embeddings for semantic search"
    )
    
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
                
                # Store files in session state
                st.session_state.files = files
                
                # Get statistics
                stats = scanner.get_stats()
                
            except Exception as e:
                st.error(f"❌ Error during scan: {str(e)}")
                return
        
        # Build search index if enabled
        if enable_indexing and files:
            with st.spinner("🧠 Building semantic search index..."):
                try:
                    # Filter for text-based files
                    text_files = [
                        f for f in files 
                        if f.extension.lower() in {".txt", ".pdf", ".docx"}
                    ]
                    
                    if text_files:
                        # Initialize extractor and model
                        extractor = TextExtractor()
                        
                        if st.session_state.embedding_model is None:
                            st.session_state.embedding_model = EmbeddingModel()
                        
                        model = st.session_state.embedding_model
                        
                        # Extract text from files
                        texts = []
                        valid_files = []
                        file_metadata = []
                        
                        progress_bar = st.progress(0)
                        for idx, file in enumerate(text_files):
                            text = extractor.extract_text(Path(file.full_path))
                            if text and len(text.strip()) > 0:
                                texts.append(text[:5000])  # Limit to first 5000 chars
                                valid_files.append(file.full_path)
                                file_metadata.append({
                                    "name": file.name,
                                    "extension": file.extension,
                                    "size": file.size_bytes
                                })
                            
                            progress_bar.progress((idx + 1) / len(text_files))
                        
                        progress_bar.empty()
                        
                        if texts:
                            # Generate embeddings
                            embeddings = model.encode_batch(texts, show_progress=False)
                            
                            # Create and populate index
                            index = VectorIndex(model.get_embedding_dimension())
                            index.add(embeddings, valid_files, file_metadata)
                            
                            st.session_state.index = index
                            
                            st.success(f"✅ Indexed {len(valid_files)} text files for search")
                        else:
                            st.warning("⚠️ No text content could be extracted")
                    else:
                        st.info("ℹ️ No text-based files (.txt, .pdf, .docx) found")
                        
                except Exception as e:
                    st.error(f"❌ Error building index: {str(e)}")
                    logger.error(f"Indexing error: {e}", exc_info=True)
        
        # Analyze files for safe-to-delete recommendations
        with st.spinner("🔍 Analyzing files for deletion safety..."):
            try:
                # Detect duplicates
                duplicate_detector = DuplicateDetector()
                for file in files:
                    duplicate_detector.add_file(file.full_path, file.size_bytes)
                
                duplicate_groups = duplicate_detector.find_duplicates()
                
                # Build duplicate map (file_path -> duplicate_count)
                duplicate_map = {}
                for group in duplicate_groups:
                    for file_path in group.file_paths:
                        duplicate_map[file_path] = len(group.file_paths) - 1
                
                # Analyze safety
                analyzer = SafetyAnalyzer()
                recommendations = analyzer.analyze_batch(files, duplicate_map)
                
                # Store in session state
                st.session_state.recommendations = recommendations
                st.session_state.duplicate_detector = duplicate_detector
                
            except Exception as e:
                logger.error(f"Analysis error: {e}", exc_info=True)
        
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
    
    # Semantic Search Interface
    if st.session_state.index is not None:
        st.markdown("---")
        st.subheader("🔍 Semantic Search")
        st.markdown("Search files using natural language - find documents by meaning, not just keywords!")
        
        # Search input
        query = st.text_input(
            "Search query",
            placeholder="e.g., 'project documentation', 'meeting notes', 'financial reports'",
            help="Enter a natural language query to find similar documents"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            top_k = st.number_input("Results", min_value=1, max_value=50, value=10)
        with col3:
            min_similarity = st.slider("Min %", min_value=0, max_value=100, value=30, step=5)
        
        if query:
            try:
                # Generate query embedding
                query_embedding = st.session_state.embedding_model.encode(query)
                
                # Search index
                results = st.session_state.index.search(query_embedding, top_k=top_k)
                
                # Filter results by minimum similarity threshold
                min_similarity_score = min_similarity / 100.0
                filtered_results = [
                    (path, sim, meta) for path, sim, meta in results 
                    if sim >= min_similarity_score
                ]
                
                if filtered_results:
                    st.success(f"Found {len(filtered_results)} matching files (min {min_similarity}% similarity)")
                    
                    # Display results
                    search_data = []
                    for file_path, similarity, metadata in filtered_results:
                        # Convert similarity to percentage
                        similarity_pct = similarity * 100
                        
                        search_data.append({
                            "Name": metadata.get("name", Path(file_path).name),
                            "Similarity": f"{similarity_pct:.1f}%",
                            "Similarity Score": similarity,
                            "Type": metadata.get("extension", ""),
                            "Size": format_file_size(metadata.get("size", 0)),
                            "Path": file_path
                        })
                    
                    search_df = pd.DataFrame(search_data)
                    
                    st.dataframe(
                        search_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Name": st.column_config.TextColumn("File Name", width="medium"),
                            "Similarity": st.column_config.TextColumn("Match", width="small"),
                            "Similarity Score": None,  # Hide raw score
                            "Type": st.column_config.TextColumn("Type", width="small"),
                            "Size": st.column_config.TextColumn("Size", width="small"),
                            "Path": st.column_config.TextColumn("Full Path", width="large")
                        }
                    )
                    
                    # Explanation
                    with st.expander("ℹ️ How does semantic search work?"):
                        st.markdown("""
                        **Semantic search** finds files based on meaning, not just keywords:
                        
                        1. **Embeddings**: Each document is converted to a 384-dimensional vector that captures its meaning
                        2. **Vector Index**: FAISS stores these vectors for fast similarity search
                        3. **Query**: Your search is also converted to a vector
                        4. **Similarity**: FAISS finds documents with vectors closest to your query
                        
                        **Example**: Searching for "budget planning" might find files containing 
                        "financial forecast" or "expense allocation" even without those exact words!
                        
                        **Similarity score**: Higher = more similar (100% = identical)
                        """)
                else:
                    st.info("No results found. Try a different query.")
                    
            except Exception as e:
                st.error(f"❌ Search error: {str(e)}")
                logger.error(f"Search error: {e}", exc_info=True)
    
    # Safe-to-Delete Recommendations
    if st.session_state.recommendations is not None:
        st.markdown("---")
        st.subheader("🗑️ Safe-to-Delete Recommendations")
        
        # Disclaimer
        st.warning("""
        ⚠️ **IMPORTANT DISCLAIMER**
        
        These are AI-assisted recommendations based on file metadata. 
        **FileSense does NOT automatically delete files.**
        
        - Always review recommendations carefully before deleting
        - We are not responsible for any data loss
        - When in doubt, keep the file or make a backup
        """)
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            min_safety_score = st.slider(
                "Minimum Safety Score",
                min_value=0,
                max_value=100,
                value=60,
                step=5,
                help="Only show files with safety score above this threshold"
            )
        with col2:
            max_results = st.number_input(
                "Max Results",
                min_value=10,
                max_value=200,
                value=50,
                step=10
            )
        with col3:
            risk_filter = st.selectbox(
                "Risk Level",
                options=["All", "LOW", "MEDIUM", "HIGH"],
                index=0
            )
        
        # Filter recommendations
        filtered_recs = [
            r for r in st.session_state.recommendations
            if r.safety_score >= min_safety_score
        ]
        
        if risk_filter != "All":
            filtered_recs = [r for r in filtered_recs if r.risk_level == risk_filter]
        
        filtered_recs = filtered_recs[:max_results]
        
        if filtered_recs:
            st.success(f"Found {len(filtered_recs)} files that may be safe to delete")
            
            # Display recommendations
            for idx, rec in enumerate(filtered_recs, 1):
                with st.expander(
                    f"#{idx} - {rec.file_name} - {rec.safety_score}% safe ({rec.risk_level} risk)",
                    expanded=(idx <= 5)  # Expand first 5
                ):
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        st.write(f"**File:** `{rec.file_name}`")
                        st.write(f"**Path:** `{rec.file_path}`")
                        st.write(f"**Size:** {format_file_size(rec.size_bytes)}")
                        st.write(f"**Last Accessed:** {rec.last_accessed.strftime('%Y-%m-%d')}")
                        
                        # Reasons
                        st.write("**Why it may be safe to delete:**")
                        for reason in rec.reasons:
                            st.write(f"• {reason}")
                    
                    with col_b:
                        # Visual score indicator
                        score_color = "#28a745" if rec.risk_level == "LOW" else "#ffc107" if rec.risk_level == "MEDIUM" else "#dc3545"
                        st.markdown(f"""
                        <div style="text-align: center; padding: 20px; background-color: {score_color}; border-radius: 10px; color: white;">
                            <h1 style="margin: 0;">{rec.safety_score}%</h1>
                            <p style="margin: 0;">SAFE</p>
                            <p style="margin: 0; font-size: 0.9em;">{rec.risk_level} RISK</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Summary statistics
            st.markdown("---")
            st.subheader("📊 Recommendation Summary")
            
            total_size = sum(r.size_bytes for r in filtered_recs)
            risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            for r in filtered_recs:
                risk_counts[r.risk_level] += 1
            
            col_x, col_y, col_z, col_w = st.columns(4)
            with col_x:
                st.metric("Total Files", len(filtered_recs))
            with col_y:
                st.metric("Potential Space", format_file_size(total_size))
            with col_z:
                st.metric("Low Risk", risk_counts["LOW"])
            with col_w:
                st.metric("Medium Risk", risk_counts["MEDIUM"])
            
            # Explanation of scoring
            with st.expander("ℹ️ How does the safety scoring work?"):
                st.markdown("""
                **FileSense uses transparent, rule-based scoring (NO machine learning)**
                
                Files are scored based on 4 factors:
                
                1. **Last Accessed Time (0-40 points)**
                   - Not accessed in 2+ years = 40 points
                   - Not accessed in 1+ year = 35 points
                   - Recently accessed = 0 points
                
                2. **File Type (0-30 points)**
                   - Temporary files (.tmp, .cache) = 30 points
                   - Backup files = 20 points
                   - Log files = 15 points
                   - Regular files = 0 points
                
                3. **File Size (0-15 points)**
                   - Very small files (<1KB) = 15 points
                   - Large files (>100MB) = 0 points
                   - Smaller files are safer to delete
                
                4. **Duplicates (0-15 points)**
                   - 3+ duplicates exist = 15 points
                   - 1 duplicate exists = 10 points
                   - No duplicates = 0 points
                
                **Total Score:**
                - 70-100 = LOW risk (likely safe)
                - 40-69 = MEDIUM risk (review carefully)
                - 0-39 = HIGH risk (keep unless certain)
                
                **Why this is safer than auto-delete:**
                - All decisions are transparent and explainable
                - You review each file before deleting
                - No "black box" algorithms
                - Multiple factors considered together
                """)
        else:
            st.info("No files match the current filter criteria")
    
    # Welcome screen (only show if no files scanned)
    if st.session_state.files is None:
        st.info("👈 Enter a folder path and click **Start Scan** to begin")
        
        st.markdown("""
        ### How to use:
        1. Enter a folder path in the sidebar (or use the default)
        2. Choose whether to scan subdirectories
        3. Set the maximum scan depth
        4. Enable **Build search index** for semantic search
        5. Click **Start Scan**
        
        ### Features:
        - 📁 **File Scanner**: List all files with metadata
        - 🧠 **Semantic Search**: Find files using natural language (supports .txt, .pdf, .docx)
        - �️ **Safe-to-Delete**: Rule-based recommendations for cleaning up files
        - 🔍 **Duplicate Detection**: Find identical files by content hash
        - 🔒 **Safe**: System folders skipped, permission errors handled
        - 🚀 **Fast**: Efficient indexing with FAISS
        
        ### What makes Safe-to-Delete recommendations safe?
        - **Transparent scoring**: All decisions based on clear rules (last accessed, file type, size, duplicates)
        - **No auto-delete**: You manually review every file before deletion
        - **Explainable**: Each recommendation shows exactly why it's considered safe
        - **Risk levels**: LOW/MEDIUM/HIGH labels help you decide
        
        Unlike tools that automatically delete files, FileSense gives you the information to make informed decisions!
        """)


if __name__ == "__main__":
    main()
