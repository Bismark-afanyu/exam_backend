"""Firebase Storage helpers.

Exam PDFs are stored with default (private) ACL. Access is granted
through short-lived v4 signed URLs generated on demand — the backend
credentials carry the service-account signing key, so this works both
locally and on Cloud Run without extra IAM setup.
"""

from datetime import timedelta

from google.cloud.storage import Blob

# v4 signed URLs are capped at 7 days; stay under it.
SIGNED_URL_TTL = timedelta(days=6)


def generate_signed_pdf_url(blob: Blob) -> str:
    return blob.generate_signed_url(
        version="v4", expiration=SIGNED_URL_TTL, method="GET"
    )
