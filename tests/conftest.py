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

@pytest.fixture
def client(mock_db, mock_current_user):
    """Fixture for FastAPI TestClient with mocked DB and auth dependency."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
