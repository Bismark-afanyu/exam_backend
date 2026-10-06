import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from google.cloud.firestore import Client

from app.api.deps import get_current_editor, get_current_user
from app.core.file_validation import MAX_PDF_BYTES, validate_pdf_upload
from app.db.firebase import get_db, get_storage_bucket
from app.repositories.exam import ExamRepository
from app.schemas.exam import ExamPaperData
from app.services.pdf.processor import ExamPaperProcessor
from app.services.storage import generate_signed_pdf_url

logger = logging.getLogger(__name__)

router = APIRouter()
processor = ExamPaperProcessor()


@router.post("/save")
async def save_exam_data(
    exam_data: ExamPaperData,
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_editor),
):
    try:
        repository = ExamRepository(db)

        # Check for duplication
        if repository.check_exam_exists(
            exam_data.subject, exam_data.year, exam_data.paper
        ):
            logger.warning(
                f"Duplicate exam upload prevented: {exam_data.subject} {exam_data.year} Paper {exam_data.paper}"
            )
            raise HTTPException(
                status_code=409,
                detail=f"This exact exam paper ({exam_data.subject}, Year {exam_data.year}, Paper {exam_data.paper}) has already been saved to the database.",
            )

        return repository.save_full_exam(exam_data)
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to save exam data to Firestore", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error saving exam data."
        ) from None


@router.post("/upload")
async def upload_exam_paper(
    file: UploadFile = File(...),
    _: dict[str, Any] = Depends(get_current_editor),
):
    await validate_pdf_upload(file)

    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    if tmp_path.stat().st_size > MAX_PDF_BYTES:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail=f"PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB size limit",
        )

    try:
        # Process the PDF using the orchestrator
        result = processor.process_exam_paper(tmp_path)
        return {"message": "Exam paper processed successfully", "data": result}
    except Exception:
        logger.error("Error processing uploaded exam PDF", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error processing PDF."
        ) from None
    finally:
        # Clean up the temporary file
        if tmp_path.exists():
            os.remove(tmp_path)


@router.get("/")
async def list_exams(
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
):
    """
    Returns a list of all unique exams stored in the database.
    """
    try:
        repository = ExamRepository(db)
        exams = repository.get_all_exams()
        return [_resolve_pdf_url(exam) for exam in exams]
    except Exception:
        logger.error("Failed to list exams", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error listing exams."
        ) from None


@router.get("/{subject}/{year}/{paper}", response_model=ExamPaperData)
async def get_exam(
    subject: str,
    year: int,
    paper: int,
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
):
    """
    Returns the full structured data for a specific exam.
    """
    try:
        repository = ExamRepository(db)
        exam_data = repository.get_full_exam(subject, year, paper)

        if not exam_data:
            raise HTTPException(
                status_code=404,
                detail=f"Exam not found: {subject}, Year {year}, Paper {paper}",
            )

        return exam_data
    except HTTPException:
        raise
    except Exception:
        logger.error(f"Failed to fetch exam {subject} {year} P{paper}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error fetching exam."
        ) from None


@router.post("/{subject}/{year}/{paper}/pdf")
async def upload_exam_pdf(
    subject: str,
    year: int,
    paper: int,
    file: UploadFile = File(...),
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_editor),
):
    """
    Uploads a PDF file to Firebase Storage (kept private) and stores its
    object path in exam_metadata. Clients receive a signed URL.
    """
    await validate_pdf_upload(file)

    try:
        bucket = get_storage_bucket()

        # Generate a unique filename
        safe_subject = subject.lower().replace(" ", "_")
        blob_name = f"exams/{safe_subject}/{year}/paper_{paper}.pdf"
        blob = bucket.blob(blob_name)

        # Upload the file (no public ACL is granted)
        file_content = await file.read()
        blob.upload_from_string(file_content, content_type="application/pdf")

        pdf_url = generate_signed_pdf_url(blob)

        # Update exam_metadata with the PDF object path (signed URLs are
        # generated fresh on read — never persisted, they expire)
        metadata_ref = db.collection("exam_metadata").document(
            f"{subject}_{year}_{paper}".lower().replace(" ", "_")
        )
        metadata_ref.update({"pdf_path": blob_name})

        return {"status": "success", "pdf_url": pdf_url}
    except Exception:
        logger.error(f"Failed to upload PDF for {subject} {year} P{paper}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error uploading PDF."
        ) from None


def _resolve_pdf_url(exam: dict[str, Any]) -> dict[str, Any]:
    """Prefers a fresh signed URL derived from the stored object path;
    keeps the legacy public URL for metadata saved before private ACLs."""
    pdf_path = exam.get("pdf_path")
    if not pdf_path:
        return exam
    try:
        blob = get_storage_bucket().blob(pdf_path)
        exam["pdf_url"] = generate_signed_pdf_url(blob)
    except Exception:
        logger.warning(f"Could not sign PDF URL for {pdf_path}", exc_info=True)
    return exam
