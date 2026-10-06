import pytest

VALID_PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"


def test_upload_exam_pdf_invalid_type(editor_client):
    # Testing with a text file instead of PDF
    files = {"file": ("test.txt", b"not a pdf", "text/plain")}
    response = editor_client.post("/api/v1/exams/upload", files=files)

    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json()["detail"]


def test_upload_exam_pdf_fake_extension(editor_client):
    # .pdf filename but the bytes are not a PDF — the suffix alone must not pass
    files = {"file": ("fake.pdf", b"this is definitely not a pdf", "application/pdf")}
    response = editor_client.post("/api/v1/exams/upload", files=files)

    assert response.status_code == 400
    assert "not a valid PDF" in response.json()["detail"]


def test_upload_exam_pdf_too_large(editor_client, monkeypatch):
    from app.api.v1.endpoints import exams as exams_module

    monkeypatch.setattr(exams_module, "MAX_PDF_BYTES", 8)
    files = {"file": ("big.pdf", VALID_PDF_BYTES + b"0" * 100, "application/pdf")}
    response = editor_client.post("/api/v1/exams/upload", files=files)

    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_upload_exam_pdf_rejects_magic_bytes_only_lookalike(editor_client):
    # Header must be exactly the PDF magic — a file starting mid-stream fails
    files = {"file": ("offset.pdf", b"xx%PDF-1.4 rest of document", "application/pdf")}
    response = editor_client.post("/api/v1/exams/upload", files=files)

    assert response.status_code == 400


@pytest.mark.skip(reason="Needs real PDF or a mockable processor — Gemini call involved")
def test_upload_exam_pdf_success(editor_client):
    from pathlib import Path

    pdf_path = Path("Mid-Semester Assessment .pdf")
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            response = editor_client.post("/api/v1/exams/upload", files=files)

            assert response.status_code == 200
            assert "data" in response.json()
