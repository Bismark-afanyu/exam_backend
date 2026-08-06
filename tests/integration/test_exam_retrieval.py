import pytest
from unittest.mock import MagicMock, patch
from app.models.exam import Question, Subject

@pytest.fixture
def mock_collections(mock_db):
    collections = {}
    def get_collection(name):
        if name not in collections:
            collections[name] = MagicMock()
        return collections[name]
    mock_db.collection.side_effect = get_collection
    
    # Pre-initialize common collections to avoid KeyErrors in tests
    for name in ["questions", "subjects", "years", "subquestions", "diagrams", "figures"]:
        get_collection(name)
        
    return collections

def test_list_exams_empty(client, mock_collections):
    mock_collections["questions"].stream.return_value = []
    
    response = client.get("/api/v1/exams/")
    assert response.status_code == 200
    assert response.json() == []

def test_list_exams_success(client, mock_collections):
    mock_doc1 = MagicMock()
    mock_doc1.id = "q1"
    mock_doc1.to_dict.return_value = {
        "subject": "Maths",
        "year": 2024,
        "paper": 1,
        "question_number": "1",
        "question_text": "Solve x",
        "topic": "Algebra",
        "subtopic": "Equations",
        "marks_total": 5,
        "question_type": "Calculation",
        "has_diagram": False,
        "has_figure": False,
        "has_subquestions": False
    }
    
    mock_collections["questions"].stream.return_value = [mock_doc1]
    
    response = client.get("/api/v1/exams/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert {"subject": "Maths", "year": 2024, "paper": 1}.items() <= data[0].items()

def test_get_exam_not_found(client, mock_collections):
    mock_collections["questions"].where.return_value.where.return_value.stream.return_value = []
    
    response = client.get("/api/v1/exams/Maths/2024/1")
    assert response.status_code == 404

def test_get_exam_success(client, mock_collections):
    # 1. Mock questions
    mock_q_doc = MagicMock()
    mock_q_doc.id = "q1"
    mock_q_doc.to_dict.return_value = {
        "subject": "Maths",
        "year": 2024,
        "paper": 1,
        "question_number": "1",
        "question_text": "Solve x",
        "topic": "Algebra",
        "subtopic": "Equations",
        "marks_total": 5,
        "question_type": "Calculation",
        "has_diagram": False,
        "has_figure": False,
        "has_subquestions": False,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    
    # Mock the where chain for questions (2 filters: year and paper)
    mock_collections["questions"].where.return_value.where.return_value.stream.return_value = [mock_q_doc]
    
    # 2. Mock subqueries for subquestions, diagrams, figures
    mock_collections["subquestions"].where.return_value.stream.return_value = []
    mock_collections["diagrams"].where.return_value.stream.return_value = []
    mock_collections["figures"].where.return_value.stream.return_value = []
    
    # 3. Mock subject for level
    mock_s_doc = MagicMock()
    mock_s_doc.id = "maths"
    mock_s_doc.exists = True
    mock_s_doc.to_dict.return_value = {"name": "Maths", "level": "A-Level"}
    mock_collections["subjects"].document.return_value.get.return_value = mock_s_doc
    
    response = client.get("/api/v1/exams/Maths/2024/1")
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "Maths"
    assert data["level"] == "A-Level"
    assert len(data["questions"]) == 1
