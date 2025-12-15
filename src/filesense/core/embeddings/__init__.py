"""
Embeddings module for semantic search.

This module handles the generation of text embeddings using
pre-trained transformer models for semantic similarity search.
"""

from .model import EmbeddingModel
from .index import VectorIndex

__all__ = ["EmbeddingModel", "VectorIndex"]
