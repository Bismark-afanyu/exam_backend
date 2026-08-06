import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from google.cloud.firestore import Client

from app.api.deps import get_current_user
from app.db.firebase import get_db, get_storage_bucket
from app.repositories.exam import ExamRepository
from app.schemas.exam import ExamPaperData
from app.services.pdf.processor import ExamPaperProcessor

logger = logging.getLogger(__name__)

router = APIRouter()
processor = ExamPaperProcessor()


@router.post("/save")
async def save_exam_data(
    exam_data: ExamPaperData,
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
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
    except Exception as e:
        logger.error("Failed to save exam data to Firestore", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error saving exam data: {str(e)}") from e


@router.post("/upload")
async def upload_exam_paper(
    file: UploadFile = File(...),
    _: dict[str, Any] = Depends(get_current_user),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        # Process the PDF using the orchestrator
        result = processor.process_exam_paper(tmp_path)
        return {"message": "Exam paper processed successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}") from e
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
        return repository.get_all_exams()
    except Exception as e:
        logger.error("Failed to list exams", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing exams: {str(e)}") from e


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
    except Exception as e:
        logger.error(f"Failed to fetch exam {subject} {year} P{paper}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching exam: {str(e)}") from e


@router.post("/{subject}/{year}/{paper}/pdf")
async def upload_exam_pdf(
    subject: str,
    year: int,
    paper: int,
    file: UploadFile = File(...),
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
):
    """
    Uploads a PDF file to Firebase Storage and saves the URL in exam_metadata.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        bucket = get_storage_bucket()

        # Generate a unique filename
        safe_subject = subject.lower().replace(" ", "_")
        blob_name = f"exams/{safe_subject}/{year}/paper_{paper}.pdf"
        blob = bucket.blob(blob_name)

        # Upload the file
        file_content = await file.read()
        blob.upload_from_string(file_content, content_type="application/pdf")

        # Make the blob publicly accessible
        blob.make_public()
        pdf_url = blob.public_url

        # Update exam_metadata with the PDF URL
        metadata_ref = db.collection("exam_metadata").document(
            f"{subject}_{year}_{paper}".lower().replace(" ", "_")
        )
        metadata_ref.update({"pdf_url": pdf_url})

        return {"status": "success", "pdf_url": pdf_url}
    except Exception as e:
        logger.error(f"Failed to upload PDF for {subject} {year} P{paper}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading PDF: {str(e)}") from e
