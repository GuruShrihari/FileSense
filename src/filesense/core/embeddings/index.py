"""FAISS-based vector index for semantic similarity search."""

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
    """FAISS vector index using cosine similarity (IndexFlatIP + L2 normalization)."""
    
    def __init__(self, embedding_dim: int) -> None:
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss-cpu not installed. "
                "Install with: pip install faiss-cpu"
            )
        
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatIP(embedding_dim)
        self.file_paths: List[str] = []
        self.file_metadata: List[Dict] = []
        
        logger.info(f"Created FAISS index with dimension {embedding_dim}")
    
    def add(
        self, 
        embeddings: np.ndarray, 
        file_paths: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> None:
        """Add embeddings with associated file paths and metadata."""
        if embeddings.shape[0] != len(file_paths):
            raise ValueError("Number of embeddings must match number of file paths")
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} "
                f"doesn't match index dimension {self.embedding_dim}"
            )
        
        embeddings = embeddings.astype(np.float32)
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        self.file_paths.extend(file_paths)
        self.file_metadata.extend(metadata if metadata else [{} for _ in file_paths])
        
        logger.info(f"Added {len(file_paths)} items to index. Total: {self.index.ntotal}")
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 10
    ) -> List[Tuple[str, float, Dict]]:
        """Search for most similar items. Returns (path, similarity, metadata) tuples."""
        if self.index.ntotal == 0:
            return []
        
        query = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query)
        
        k = min(top_k, self.index.ntotal)
        similarities, indices = self.index.search(query, k)
        
        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx != -1:
                results.append((
                    self.file_paths[idx],
                    float(similarity),
                    self.file_metadata[idx],
                ))
        
        return results
    
    def save(self, save_dir: str) -> None:
        """Persist the FAISS index and metadata to disk."""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        faiss.write_index(self.index, str(save_path / "faiss_index.bin"))
        
        with open(save_path / "metadata.pkl", "wb") as f:
            pickle.dump({
                "file_paths": self.file_paths,
                "file_metadata": self.file_metadata,
                "embedding_dim": self.embedding_dim
            }, f)
        
        logger.info(f"Index saved to {save_dir}")
    
    def load(self, save_dir: str) -> None:
        """Load a previously saved FAISS index and metadata."""
        save_path = Path(save_dir)
        
        index_file = save_path / "faiss_index.bin"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")
        self.index = faiss.read_index(str(index_file))
        
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
        self.index.reset()
        self.file_paths.clear()
        self.file_metadata.clear()
    
    def get_stats(self) -> dict:
        return {
            "total_items": self.index.ntotal,
            "embedding_dim": self.embedding_dim,
            "is_trained": self.index.is_trained
        }
