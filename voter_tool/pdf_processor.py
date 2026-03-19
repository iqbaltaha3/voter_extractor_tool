from pdf2image import convert_from_path
from pathlib import Path

class PDFProcessor:
    """Convert PDF pages to PIL images."""
    def __init__(self, dpi: int = 400):
        self.dpi = dpi

    def convert(self, pdf_path: Path):
        try:
            return convert_from_path(str(pdf_path), dpi=self.dpi)
        except Exception as e:
            raise RuntimeError(f"PDF conversion failed: {e}")