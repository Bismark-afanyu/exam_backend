import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
from app.services.pdf.base import PDFExtractorBase
from pathlib import Path
from typing import Any, Dict, Union

class TextExtractor(PDFExtractorBase):
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        pdf_path = str(pdf_path)
        
        # Use PyMuPDF for quick metadata and text extraction
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        pymupdf_text = ""
        for page in doc:
            pymupdf_text += page.get_text()
        
        # Use pdfminer.six for more detailed text extraction if needed
        pdfminer_text = extract_text(pdf_path)
        
        return {
            "metadata": metadata,
            "text": {
                "pymupdf": pymupdf_text,
                "pdfminer": pdfminer_text
            },
            "pages_count": len(doc)
        }
