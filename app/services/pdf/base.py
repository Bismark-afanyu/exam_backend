from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PDFExtractorBase(ABC):
    @abstractmethod
    def extract(self, pdf_path: str | Path) -> dict[str, Any]:
        """Base method for extracting data from PDF."""
        pass
