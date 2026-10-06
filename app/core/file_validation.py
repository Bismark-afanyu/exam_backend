"""Upload validation for PDF files.

Filename suffixes and declared MIME types are client-controlled and can
be spoofed, so files are accepted only when the actual bytes carry the
PDF magic number, and size is capped to bound memory/disk usage.
"""

from fastapi import HTTPException, UploadFile, status

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB — generous for scanned exam papers
_PDF_MAGIC = b"%PDF-"


async def validate_pdf_upload(file: UploadFile) -> None:
    """Raises 400/413 unless the upload is a genuine, size-capped PDF."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    header = await file.read(len(_PDF_MAGIC))
    await file.seek(0)
    if header != _PDF_MAGIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is not a valid PDF",
        )

    if file.size is not None and file.size > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB size limit",
        )
