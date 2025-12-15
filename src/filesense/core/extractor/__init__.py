"""
Text extraction module.

This module handles safe extraction of text content from various
file formats for indexing and search purposes.
"""

from .text import TextExtractor, extract_text_from_file

__all__ = ["TextExtractor", "extract_text_from_file"]
