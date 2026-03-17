from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Union

class PDFExtractorBase(ABC):
    @abstractmethod
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """Base method for extracting data from PDF."""
        pass
