from app.services.pdf.text_extractor import TextExtractor
from app.services.pdf.table_extractor import TableExtractor
from app.services.ai.structured_parser import ExamAIParser
from pathlib import Path
from typing import Any, Dict, Union

class ExamPaperProcessor:
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.doc_parser = ExamAIParser()

    def process_exam_paper(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
            
        print(f"🚀 Processing exam paper: {pdf_path.name}")
        
        # 1. Render PDF to images for Multimodal Vision AI
        images_bytes = self.render_to_images(pdf_path)
        
        # 2. Parse images into structured ExamPaperData using Gemini
        print(f"🤖 Sending {len(images_bytes)} pages to AI for structured parsing...")
        structured_data = self.doc_parser.parse_images(images_bytes)
        
        # Return as a dictionary matching the Pydantic schema
        return structured_data.model_dump()

    def render_to_images(self, pdf_path: Union[str, Path], dpi: int = 150) -> list[bytes]:
        """
        Renders each page of the PDF into a high-resolution PNG image byte stream.
        This is required for Multimodal Vision extraction of scanned documents.
        """
        import fitz # PyMuPDF
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
            
        print(f"📸 Rendering {pdf_path.name} to images (DPI: {dpi})...")
        images_bytes = []
        
        # Open document with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Create a Matrix for zooming/DPI
        # PyMuPDF default is 72 DPI. So zoom = DPI / 72
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            images_bytes.append(img_bytes)
            print(f"   - Rendered page {page_num + 1}/{len(doc)}")
            
        doc.close()
        return images_bytes

