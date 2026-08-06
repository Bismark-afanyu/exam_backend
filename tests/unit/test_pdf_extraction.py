from pathlib import Path

import pytest

from app.services.pdf.text_extractor import TextExtractor


def test_text_extractor_interface():
    extractor = TextExtractor()
    assert hasattr(extractor, "extract")

@pytest.mark.skip(reason="Requires a sample PDF")
def test_text_extraction_real_file():
    extractor = TextExtractor()
    path = Path("Mid-Semester Assessment .pdf")
    if path.exists():
        result = extractor.extract(path)
        assert "text" in result
        assert "pymupdf" in result["text"]
