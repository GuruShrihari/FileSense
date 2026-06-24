"""Text extraction from .txt, .pdf, and .docx files."""

from .text import TextExtractor, extract_text_from_file

__all__ = ["TextExtractor", "extract_text_from_file"]
