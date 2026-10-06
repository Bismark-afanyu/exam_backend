from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.firebase import get_db
from app.main import app


@pytest.fixture
def mock_db():
    """Fixture to mock Firestore DB."""
    return MagicMock()

@pytest.fixture
def mock_current_user():
    """Fixture for an authenticated user returned by get_current_user."""
    return {
        "id": "test@example.com",
        "full_name": "Test Student",
        "email": "test@example.com",
        "role": "student",
    }

def _make_client(mock_db, user):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}


@pytest.fixture
def client(mock_db, mock_current_user):
    """Fixture for FastAPI TestClient with mocked DB and auth dependency."""
    yield from _make_client(mock_db, mock_current_user)


@pytest.fixture
def editor_client(mock_db, mock_current_user):
    """Client authenticated as an editor — the role allowed to write exam content."""
    yield from _make_client(mock_db, {**mock_current_user, "role": "editor"})


@pytest.fixture
def admin_client(mock_db, mock_current_user):
    """Client authenticated as an admin."""
    yield from _make_client(mock_db, {**mock_current_user, "role": "admin"})

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
