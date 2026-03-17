from app.services.pdf.text_extractor import TextExtractor
from app.services.pdf.table_extractor import TableExtractor
from pathlib import Path
from typing import Any, Dict, Union

class ExamPaperProcessor:
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()

    def process_exam_paper(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
            
        print(f"🚀 Processing exam paper: {pdf_path.name}")
        
        text_data = self.text_extractor.extract(pdf_path)
        table_data = self.table_extractor.extract(pdf_path)
        
        return {
            "filename": pdf_path.name,
            "text_content": text_data,
            "tables": table_data
        }
