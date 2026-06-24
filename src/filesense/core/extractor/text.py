"""Text extraction from .txt, .pdf, and .docx files."""

from pathlib import Path
from typing import Optional
import logging

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extract text content from .txt, .pdf, and .docx files."""
    
    SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}
    
    def __init__(self) -> None:
        self.files_processed = 0
        self.files_failed = 0
    
    def can_extract(self, file_path: Path) -> bool:
        """Check if the file format is supported and its library is available."""
        extension = file_path.suffix.lower()
        
        if extension not in self.SUPPORTED_EXTENSIONS:
            return False
        if extension == ".pdf" and not PDF_AVAILABLE:
            logger.warning("PyPDF2 not available — cannot extract PDF")
            return False
        if extension == ".docx" and not DOCX_AVAILABLE:
            logger.warning("python-docx not available — cannot extract DOCX")
            return False
        
        return True
    
    def extract_text(self, file_path: Path, max_chars: int = 100000) -> Optional[str]:
        """Extract text content with a character limit for memory safety."""
        if not self.can_extract(file_path):
            return None
        
        extension = file_path.suffix.lower()
        
        try:
            if extension == ".txt":
                text = self._extract_txt(file_path, max_chars)
            elif extension == ".pdf":
                text = self._extract_pdf(file_path, max_chars)
            elif extension == ".docx":
                text = self._extract_docx(file_path, max_chars)
            else:
                return None
            
            if text:
                self.files_processed += 1
                return text
            else:
                self.files_failed += 1
                return None
                
        except Exception as e:
            self.files_failed += 1
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None
    
    def _extract_txt(self, file_path: Path, max_chars: int) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read(max_chars).strip()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read(max_chars).strip()
            except Exception as e:
                logger.error(f"Failed to read text file {file_path}: {e}")
                return None
    
    def _extract_pdf(self, file_path: Path, max_chars: int) -> Optional[str]:
        if not PDF_AVAILABLE:
            return None
        
        try:
            reader = PdfReader(str(file_path))
            text_parts = []
            total_chars = 0
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                    total_chars += len(page_text)
                    if total_chars >= max_chars:
                        break
            
            return "\n".join(text_parts)[:max_chars].strip()
            
        except Exception as e:
            logger.error(f"Failed to extract PDF {file_path}: {e}")
            return None
    
    def _extract_docx(self, file_path: Path, max_chars: int) -> Optional[str]:
        if not DOCX_AVAILABLE:
            return None
        
        try:
            doc = Document(str(file_path))
            text_parts = []
            total_chars = 0
            
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_parts.append(paragraph.text)
                    total_chars += len(paragraph.text)
                    if total_chars >= max_chars:
                        break
            
            return "\n".join(text_parts)[:max_chars].strip()
            
        except Exception as e:
            logger.error(f"Failed to extract DOCX {file_path}: {e}")
            return None
    
    def get_stats(self) -> dict:
        return {
            "files_processed": self.files_processed,
            "files_failed": self.files_failed
        }


def extract_text_from_file(file_path: str, max_chars: int = 100000) -> Optional[str]:
    """Convenience function to extract text from a file path string."""
    extractor = TextExtractor()
    return extractor.extract_text(Path(file_path), max_chars)
