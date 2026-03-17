from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.pdf.processor import ExamPaperProcessor
from pathlib import Path
import shutil
import os
import tempfile

from app.schemas.exam import ExamPaperData
from app.repositories.exam import ExamRepository
from app.db.firebase import get_db

router = APIRouter()
processor = ExamPaperProcessor()

@router.post("/save")
async def save_exam_data(exam_data: ExamPaperData):
    try:
        db = get_db()
        repository = ExamRepository(db)
        result = repository.save_full_exam(exam_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving exam data: {str(e)}")

@router.post("/upload")
async def upload_exam_paper(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
        
    try:
        # Process the PDF using the orchestrator
        result = processor.process_exam_paper(tmp_path)
        return {
            "message": "Exam paper processed successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    finally:
        # Clean up the temporary file
        if tmp_path.exists():
            os.remove(tmp_path)
