import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.db.firebase import get_db

@pytest.fixture
def mock_db():
    """Fixture to mock Firestore DB."""
    mock = MagicMock()
    return mock

@pytest.fixture
def client(mock_db):
    """Fixture for FastAPI TestClient with mocked DB dependency."""
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
