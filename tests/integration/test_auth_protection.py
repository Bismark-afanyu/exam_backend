import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def unauth_client():
    """TestClient with Firestore mocked but WITHOUT the auth dependency override,
    so protected endpoints must reject requests that carry no token."""
    from unittest.mock import MagicMock

    from app.db.firebase import get_db

    app.dependency_overrides[get_db] = lambda: MagicMock()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


PROTECTED_REQUESTS = (
    ("get", "/api/v1/exams/"),
    ("post", "/api/v1/exams/upload"),
    ("post", "/api/v1/exams/save"),
    ("get", "/api/v1/exams/Maths/2024/1"),
    ("post", "/api/v1/exams/Maths/2024/1/pdf"),
    ("get", "/api/v1/items/"),
    ("post", "/api/v1/items/"),
    ("get", "/api/v1/items/abc"),
    ("put", "/api/v1/items/abc"),
    ("delete", "/api/v1/items/abc"),
    ("get", "/api/v1/auth/me"),
)


@pytest.mark.parametrize(("method", "path"), PROTECTED_REQUESTS)
def test_protected_endpoint_requires_token(unauth_client, method, path):
    response = unauth_client.request(method, path)
    assert response.status_code == 401, (
        f"{method.upper()} {path} should require auth"
    )


@pytest.mark.parametrize(("method", "path"), PROTECTED_REQUESTS)
def test_protected_endpoint_rejects_bad_token(unauth_client, method, path):
    response = unauth_client.request(
        method, path, headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401, (
        f"{method.upper()} {path} should reject bad token"
    )


PUBLIC_ENDPOINTS = (
    (
        "post",
        "/api/v1/auth/register",
        {"full_name": "A", "email": "a@b.com", "password": "secret123"},
    ),
    ("post", "/api/v1/auth/login", {"email": "a@b.com", "password": "secret123"}),
    ("post", "/api/v1/auth/google", {"id_token": "fake-firebase-token"}),
)


@pytest.mark.parametrize(("method", "path", "payload"), PUBLIC_ENDPOINTS)
def test_public_endpoints_do_not_require_token(unauth_client, method, path, payload):
    response = unauth_client.request(method, path, json=payload)
    is_missing_credentials = (
        response.status_code == 401
        and response.json().get("detail") == "Not authenticated"
    )
    assert not is_missing_credentials, f"{method.upper()} {path} should be public"

