"""Embedding model wrapper using sentence-transformers."""

from typing import List, Optional
import logging
import sys
import numpy as np

# In PyInstaller frozen builds, sentence_transformers is bundled but its import
# can still fail due to sub-dependency issues (tokenizers native DLLs, torch
# path resolution, etc.).  Catch *all* exceptions so the real error surfaces
# instead of a misleading "not installed" message.
_TRANSFORMERS_IMPORT_ERROR: Optional[BaseException] = None
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except Exception as _imp_err:
    TRANSFORMERS_AVAILABLE = False
    _TRANSFORMERS_IMPORT_ERROR = _imp_err
    logging.getLogger(__name__).warning(
        "sentence_transformers import failed: %s", _imp_err, exc_info=True
    )

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for sentence-transformer models.

    Uses 'all-MiniLM-L6-v2' by default — a small, fast model (384-dim embeddings, ~80MB).
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(self, model_name: Optional[str] = None) -> None:
        if not TRANSFORMERS_AVAILABLE:
            # Provide the *real* failure reason, not just "not installed"
            if getattr(sys, "frozen", False) and _TRANSFORMERS_IMPORT_ERROR is not None:
                raise ImportError(
                    f"sentence-transformers failed to load in frozen build: "
                    f"{_TRANSFORMERS_IMPORT_ERROR}"
                ) from _TRANSFORMERS_IMPORT_ERROR
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name or self.DEFAULT_MODEL
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        dim = self.model.get_sentence_embedding_dimension()
        if dim is None:
            raise ValueError(
                f"Could not determine embedding dimension for model '{self.model_name}'."
            )
        self.embedding_dim = dim
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
    
    def encode(self, text: str) -> np.ndarray:
        """Generate embedding vector for a single text."""
        return self.model.encode(text, convert_to_numpy=True)
    
    def encode_batch(
        self, 
        texts: List[str], 
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """Generate embeddings for multiple texts in batches."""
        if not texts:
            return np.array([])
        
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
    
    def get_embedding_dimension(self) -> int:
        return self.embedding_dim
