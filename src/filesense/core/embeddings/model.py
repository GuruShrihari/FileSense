"""
Embedding model wrapper using sentence-transformers.

This module provides a simple interface for generating text embeddings
using pre-trained transformer models that run locally.
"""

from typing import List, Optional
import logging
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrapper for sentence-transformer models.
    
    Uses 'all-MiniLM-L6-v2' by default - a small, fast model that:
    - Runs on CPU efficiently
    - Generates 384-dimensional embeddings
    - Works well for semantic similarity tasks
    - Requires ~80MB of disk space
    
    What are embeddings?
    --------------------
    Embeddings are numerical representations of text that capture semantic meaning.
    Similar texts have similar embeddings (vectors close together in space).
    
    Example:
        "cat" and "kitten" → similar vectors (close together)
        "cat" and "car" → different vectors (far apart)
    """
    
    # Default model - small, fast, and accurate
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the sentence-transformer model
                       (default: all-MiniLM-L6-v2)
        
        Raises:
            ImportError: If sentence-transformers is not installed
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name or self.DEFAULT_MODEL
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
    
    def encode(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to encode
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def encode_batch(
        self, 
        texts: List[str], 
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            batch_size: Number of texts to process at once
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of shape (num_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        # Generate embeddings in batches
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this model.
        
        Returns:
            Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
        """
        return self.embedding_dim
