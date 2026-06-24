"""Semantic search embeddings using sentence-transformers and FAISS."""

from .model import EmbeddingModel
from .index import VectorIndex

__all__ = ["EmbeddingModel", "VectorIndex"]
