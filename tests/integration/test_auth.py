from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.firebase import get_db
from app.main import app

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


@pytest.fixture
def auth_client(mock_db):
    """TestClient with Firestore mocked but the REAL get_current_user dependency,
    so /me tests exercise actual token validation."""
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


def _user_dict(**overrides):
    user = {
        "id": "student@example.com",
        "full_name": "Test Student",
        "email": "student@example.com",
        "role": "student",
        "password_hash": "not-a-real-hash",
    }
    user.update(overrides)
    return user


def test_register_success(client, mock_db):
    with patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.exists.return_value = False
        mock_repo.create.return_value = _user_dict()

        response = client.post(
            REGISTER_URL,
            json={
                "full_name": "Test Student",
                "email": "student@example.com",
                "password": "secret123",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "student@example.com"
    assert data["user"]["role"] == "student"
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


def test_register_duplicate_email(client, mock_db):
    with patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.exists.return_value = True

        response = client.post(
            REGISTER_URL,
            json={
                "full_name": "Test Student",
                "email": "student@example.com",
                "password": "secret123",
            },
        )

    assert response.status_code == 409


def test_register_invalid_email(client, mock_db):
    response = client.post(
        REGISTER_URL,
        json={
            "full_name": "Test Student",
            "email": "not-an-email",
            "password": "secret123",
        },
    )
    assert response.status_code == 422


def test_login_success(client, mock_db):
    from app.core.security import hash_password

    password_hash = hash_password("secret123")
    with patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = _user_dict(password_hash=password_hash)

        response = client.post(
            LOGIN_URL,
            json={"email": "student@example.com", "password": "secret123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "student@example.com"


def test_login_wrong_password(client, mock_db):
    from app.core.security import hash_password

    password_hash = hash_password("secret123")
    with patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = _user_dict(password_hash=password_hash)

        response = client.post(
            LOGIN_URL,
            json={"email": "student@example.com", "password": "wrongpass"},
        )

    assert response.status_code == 401


def test_login_unknown_user(client, mock_db):
    with patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = None

        response = client.post(
            LOGIN_URL,
            json={"email": "nobody@example.com", "password": "secret123"},
        )

    assert response.status_code == 401


def test_me_requires_token(auth_client):
    response = auth_client.get(ME_URL)
    assert response.status_code == 401


def test_me_with_valid_token(auth_client):
    token = create_access_token(subject="student@example.com")
    with patch("app.api.deps.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = _user_dict()

        response = auth_client.get(
            ME_URL, headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert response.json()["email"] == "student@example.com"


def test_me_with_invalid_token(auth_client):
    response = auth_client.get(
        ME_URL, headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_google_auth_new_user(client, mock_db):
    with (
        patch("app.api.v1.endpoints.auth.firebase_auth.verify_id_token") as mock_verify,
        patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls,
    ):
        mock_verify.return_value = {
            "uid": "google-uid-123",
            "email": "google@example.com",
            "name": "Google User",
            "picture": "https://example.com/pic.png",
        }
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_or_create_google_user.return_value = _user_dict(
            id="google@example.com",
            full_name="Google User",
            email="google@example.com",
        )

        response = client.post(
            "/api/v1/auth/google", json={"id_token": "fake-firebase-token"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "google@example.com"
    mock_repo.get_or_create_google_user.assert_called_once()
    _, kwargs = mock_repo.get_or_create_google_user.call_args
    assert kwargs["email"] == "google@example.com"
    assert kwargs["google_uid"] == "google-uid-123"
    assert kwargs["picture_url"] == "https://example.com/pic.png"


def test_google_auth_existing_user(client, mock_db):
    with (
        patch("app.api.v1.endpoints.auth.firebase_auth.verify_id_token") as mock_verify,
        patch("app.api.v1.endpoints.auth.UserRepository") as mock_repo_cls,
    ):
        mock_verify.return_value = {
            "uid": "google-uid-123",
            "email": "existing@example.com",
        }
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_or_create_google_user.return_value = _user_dict(
            id="existing@example.com", email="existing@example.com"
        )

        response = client.post(
            "/api/v1/auth/google", json={"id_token": "fake-firebase-token"}
        )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "existing@example.com"


def test_google_auth_invalid_token(client, mock_db):
    with patch(
        "app.api.v1.endpoints.auth.firebase_auth.verify_id_token"
    ) as mock_verify:
        mock_verify.side_effect = Exception("invalid token")

        response = client.post(
            "/api/v1/auth/google", json={"id_token": "bad-token"}
        )

    assert response.status_code == 401


def test_google_auth_no_email(client, mock_db):
    with patch(
        "app.api.v1.endpoints.auth.firebase_auth.verify_id_token"
    ) as mock_verify:
        mock_verify.return_value = {"uid": "google-uid-123", "name": "No Email"}

        response = client.post(
            "/api/v1/auth/google", json={"id_token": "fake-firebase-token"}
        )

    assert response.status_code == 400
