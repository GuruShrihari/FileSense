"""
FAISS-based vector index for semantic search.

This module provides efficient similarity search using Facebook's FAISS library,
which enables fast nearest-neighbor search in high-dimensional space.
"""

from pathlib import Path
from typing import List, Tuple, Optional, Dict
import logging
import pickle
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


logger = logging.getLogger(__name__)


class VectorIndex:
    """
    FAISS-based vector index for semantic search.
    
    Why FAISS?
    ----------
    FAISS (Facebook AI Similarity Search) is optimized for:
    - Fast similarity search in large collections of vectors
    - Efficient memory usage
    - CPU and GPU support
    - Handles millions of vectors efficiently
    
    How it works:
    -------------
    1. Store file embeddings (vectors) in FAISS index
    2. When user searches, convert query to embedding
    3. FAISS finds nearest vectors (most similar files)
    4. Return files sorted by similarity score
    """
    
    def __init__(self, embedding_dim: int) -> None:
        """
        Initialize the vector index.
        
        Args:
            embedding_dim: Dimension of embeddings (e.g., 384)
        
        Raises:
            ImportError: If FAISS is not installed
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss-cpu not installed. "
                "Install with: pip install faiss-cpu"
            )
        
        self.embedding_dim = embedding_dim
        
        # Create FAISS index using Inner Product (for cosine similarity)
        # IndexFlatIP with normalized vectors = cosine similarity
        # Better for semantic search than L2 distance
        self.index = faiss.IndexFlatIP(embedding_dim)
        
        # Store metadata for each indexed item
        self.file_paths: List[str] = []
        self.file_metadata: List[Dict] = []
        
        logger.info(f"Created FAISS index with dimension {embedding_dim}")
    
    def add(
        self, 
        embeddings: np.ndarray, 
        file_paths: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """
        Add embeddings to the index.
        
        Args:
            embeddings: Array of shape (num_files, embedding_dim)
            file_paths: List of file paths corresponding to embeddings
            metadata: Optional list of metadata dicts for each file
        """
        if embeddings.shape[0] != len(file_paths):
            raise ValueError("Number of embeddings must match number of file paths")
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} "
                f"doesn't match index dimension {self.embedding_dim}"
            )
        
        # Ensure embeddings are float32 (required by FAISS)
        embeddings = embeddings.astype(np.float32)
        
        # Normalize embeddings for cosine similarity
        # This makes IndexFlatIP equivalent to cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Store metadata
        self.file_paths.extend(file_paths)
        
        if metadata:
            self.file_metadata.extend(metadata)
        else:
            self.file_metadata.extend([{} for _ in file_paths])
        
        logger.info(f"Added {len(file_paths)} items to index. Total: {self.index.ntotal}")
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 10
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search for most similar items to the query.
        
        Args:
            query_embedding: Query embedding of shape (embedding_dim,)
            top_k: Number of results to return
            
        Returns:
            List of (file_path, similarity_score, metadata) tuples,
            sorted by similarity (higher = more similar)
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty - no results to return")
            return []
        
        # Reshape query to (1, embedding_dim) and ensure float32
        query = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Normalize query for cosine similarity
        faiss.normalize_L2(query)
        
        # Limit top_k to available items
        k = min(top_k, self.index.ntotal)
        
        # Search FAISS index
        # Returns: similarity scores (inner product = cosine similarity), indices
        similarities, indices = self.index.search(query, k)
        
        # Collect results with cosine similarity scores
        # Scores range from -1 to 1 (typically 0 to 1 for similar content)
        # Higher score = more similar
        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx != -1:  # -1 means no result found
                similarity_score = float(similarity)
                file_path = self.file_paths[idx]
                metadata = self.file_metadata[idx]
                results.append((file_path, similarity_score, metadata))
        
        return results
    
    def save(self, save_dir: str) -> None:
        """
        Save the index and metadata to disk.
        
        Args:
            save_dir: Directory to save index files
        """
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = save_path / "faiss_index.bin"
        faiss.write_index(self.index, str(index_file))
        
        # Save metadata
        metadata_file = save_path / "metadata.pkl"
        with open(metadata_file, "wb") as f:
            pickle.dump({
                "file_paths": self.file_paths,
                "file_metadata": self.file_metadata,
                "embedding_dim": self.embedding_dim
            }, f)
        
        logger.info(f"Index saved to {save_dir}")
    
    def load(self, save_dir: str) -> None:
        """
        Load the index and metadata from disk.
        
        Args:
            save_dir: Directory containing saved index files
        
        Raises:
            FileNotFoundError: If index files don't exist
        """
        save_path = Path(save_dir)
        
        # Load FAISS index
        index_file = save_path / "faiss_index.bin"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")
        
        self.index = faiss.read_index(str(index_file))
        
        # Load metadata
        metadata_file = save_path / "metadata.pkl"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        
        with open(metadata_file, "rb") as f:
            data = pickle.load(f)
            self.file_paths = data["file_paths"]
            self.file_metadata = data["file_metadata"]
            self.embedding_dim = data["embedding_dim"]
        
        logger.info(f"Index loaded from {save_dir}. Total items: {self.index.ntotal}")
    
    def clear(self) -> None:
        """Clear all data from the index."""
        self.index.reset()
        self.file_paths.clear()
        self.file_metadata.clear()
        logger.info("Index cleared")
    
    def get_stats(self) -> dict:
        """
        Get index statistics.
        
        Returns:
            Dictionary with index statistics
        """
        return {
            "total_items": self.index.ntotal,
            "embedding_dim": self.embedding_dim,
            "is_trained": self.index.is_trained
        }
