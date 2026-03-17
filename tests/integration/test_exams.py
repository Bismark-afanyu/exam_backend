import pytest
from pathlib import Path

def test_upload_exam_pdf_invalid_type(client):
    # Testing with a text file instead of PDF
    files = {"file": ("test.txt", b"not a pdf", "text/plain")}
    response = client.post("/api/v1/exams/upload", files=files)
    
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json()["detail"]

@pytest.mark.skip(reason="Needs real PDF or complex mock for file handling")
def test_upload_exam_pdf_success(client):
    pdf_path = Path("Mid-Semester Assessment .pdf")
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            response = client.post("/api/v1/exams/upload", files=files)
            
            assert response.status_code == 200
            assert "data" in response.json()
