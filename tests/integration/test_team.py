from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.core.security import hash_password, verify_password
from app.main import app

LIST_URL = "/api/v1/team/members"


@pytest.fixture
def admin_user():
    return {
        "id": "admin@example.com",
        "full_name": "Admin One",
        "email": "admin@example.com",
        "role": "admin",
    }


@pytest.fixture
def admin_client(mock_db, admin_user):
    """TestClient with Firestore mocked and get_current_admin returning an admin."""
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_admin, None)


def _member_dict(**overrides):
    member = {
        "id": "editor@example.com",
        "full_name": "Editor One",
        "email": "editor@example.com",
        "role": "editor",
        "created_at": None,
    }
    member.update(overrides)
    return member


def test_non_admin_cannot_list_team(client, mock_db):
    response = client.get(LIST_URL)
    assert response.status_code == 403


def test_non_admin_cannot_create_team(client, mock_db):
    response = client.post(
        LIST_URL,
        json={
            "full_name": "Editor One",
            "email": "editor@example.com",
            "password": "secret123",
            "role": "editor",
        },
    )
    assert response.status_code == 403


def test_list_team_members(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_team_members.return_value = [
            _member_dict(),
            _member_dict(
                id="admin@example.com",
                email="admin@example.com",
                full_name="Admin One",
                role="admin",
            ),
        ]

        response = admin_client.get(LIST_URL)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["role"] == "editor"
    assert data[1]["role"] == "admin"
    assert "password_hash" not in data[0]


def test_create_team_member(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.exists.return_value = False
        mock_repo.create_team_member.return_value = _member_dict()

        response = admin_client.post(
            LIST_URL,
            json={
                "full_name": "Editor One",
                "email": "editor@example.com",
                "password": "secret123",
                "role": "editor",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "editor"
    assert data["email"] == "editor@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_create_team_member_duplicate_email(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.exists.return_value = True

        response = admin_client.post(
            LIST_URL,
            json={
                "full_name": "Editor One",
                "email": "editor@example.com",
                "password": "secret123",
                "role": "editor",
            },
        )

    assert response.status_code == 409


def test_create_team_member_invalid_role(admin_client, mock_db):
    response = admin_client.post(
        LIST_URL,
        json={
            "full_name": "Editor One",
            "email": "editor@example.com",
            "password": "secret123",
            "role": "student",
        },
    )

    assert response.status_code == 422


def test_update_team_member_role_and_password(admin_client, mock_db):
    with patch(
        "app.api.v1.endpoints.team.UserRepository"
    ) as mock_repo_cls, patch(
        "app.api.v1.endpoints.team.hash_password"
    ) as mock_hash:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = _member_dict()
        mock_repo.update_user.return_value = _member_dict(
            full_name="Editor Updated", role="admin"
        )
        mock_hash.return_value = "hashed-new-password"

        response = admin_client.patch(
            "/api/v1/team/members/editor@example.com",
            json={
                "full_name": "Editor Updated",
                "role": "admin",
                "password": "newpass123",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Editor Updated"
    assert data["role"] == "admin"
    mock_hash.assert_called_once_with("newpass123")


def test_update_team_member_not_found(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = None

        response = admin_client.patch(
            "/api/v1/team/members/missing@example.com", json={"role": "admin"}
        )

    assert response.status_code == 404


def test_update_own_role_rejected(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_email.return_value = _member_dict(
            id="admin@example.com",
            email="admin@example.com",
            full_name="Admin One",
            role="admin",
        )

        response = admin_client.patch(
            "/api/v1/team/members/admin@example.com", json={"role": "editor"}
        )

    assert response.status_code == 400


def test_delete_team_member(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.delete_by_email.return_value = True

        response = admin_client.delete("/api/v1/team/members/editor@example.com")

    assert response.status_code == 204


def test_delete_team_member_not_found(admin_client, mock_db):
    with patch("app.api.v1.endpoints.team.UserRepository") as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.delete_by_email.return_value = False

        response = admin_client.delete("/api/v1/team/members/missing@example.com")

    assert response.status_code == 404


def test_delete_self_rejected(admin_client, mock_db):
    response = admin_client.delete("/api/v1/team/members/admin@example.com")

    assert response.status_code == 400


def test_password_is_hashed_on_create():
    """The hashing helper produces a PBKDF2 string that verify_password accepts."""
    hashed = hash_password("BismarkPass")
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password("BismarkPass", hashed)
    assert not verify_password("wrong", hashed)
