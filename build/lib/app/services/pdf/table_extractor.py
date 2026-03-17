import tabula
import pdfplumber
from app.services.pdf.base import PDFExtractorBase
from pathlib import Path
from typing import Any, Dict, List, Union

class TableExtractor(PDFExtractorBase):
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        pdf_path = str(pdf_path)
        
        # Use tabula-py for specialized table extraction
        # This requires Java
        try:
            tables_tabula = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            tabula_data = [df.to_dict(orient='records') for df in tables_tabula]
        except Exception as e:
            tabula_data = f"Error in tabula extraction: {e}"
            
        # Use pdfplumber for more layout-aware table extraction
        plumber_data = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    plumber_data.append({"page": page.page_number, "tables": tables})
                    
        return {
            "tabula": tabula_data,
            "pdfplumber": plumber_data
        }
