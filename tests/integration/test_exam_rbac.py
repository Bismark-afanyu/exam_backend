"""Role-based access control on the exam content pipeline.

Any authenticated student must NOT be able to trigger the paid Gemini
extraction, write exam data, or upload PDFs to storage. Editors and
admins must pass the gate (asserted by reaching the request validation
layer, i.e. a 400 rather than a 403).
"""

import pytest

# (method, path, files/json needed to reach past the role gate)
EDITOR_GATED = (
    ("post", "/api/v1/exams/save"),
    ("post", "/api/v1/exams/upload"),
    ("post", "/api/v1/exams/Maths/2024/1/pdf"),
)

# A multipart upload that passes authz but fails request validation
BAD_FILE = {"file": ("evil.txt", b"not a pdf", "text/plain")}
MINIMAL_EXAM = {"subject": "Maths", "level": "A-Level", "year": 2024, "paper": 1}


def test_student_cannot_write_exam_content(client):
    for method, path in EDITOR_GATED:
        kwargs = {"json": MINIMAL_EXAM} if path.endswith("/save") else {"files": BAD_FILE}
        response = client.request(method, path, **kwargs)
        assert response.status_code == 403, (
            f"{method.upper()} {path} must be editor-gated, got {response.status_code}"
        )
        assert "Editor privileges" in response.json()["detail"]


@pytest.mark.parametrize("gated_client", ["editor_client", "admin_client"])
def test_editors_and_admins_pass_the_gate(gated_client, request):
    client = request.getfixturevalue(gated_client)
    for method, path in EDITOR_GATED:
        kwargs = {"json": MINIMAL_EXAM} if path.endswith("/save") else {"files": BAD_FILE}
        response = client.request(method, path, **kwargs)
        assert response.status_code != 403, (
            f"{method.upper()} {path} must allow {gated_client}"
        )


def test_reading_exams_stays_open_to_students(client):
    """Read endpoints remain available to any authenticated user."""
    assert client.get("/api/v1/exams/").status_code != 403
    assert client.get("/api/v1/exams/Maths/2024/1").status_code != 403
