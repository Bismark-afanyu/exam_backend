from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_collections(mock_db):
    collections = {}

    def get_collection(name):
        if name not in collections:
            collections[name] = MagicMock()
        return collections[name]

    mock_db.collection.side_effect = get_collection

    for name in [
        "questions",
        "subjects",
        "years",
        "topics",
        "subquestions",
        "sub_subquestions",
        "diagrams",
        "figures",
        "exam_metadata",
    ]:
        get_collection(name)

    return collections


NESTED_EXAM = {
    "subject": "Chemistry",
    "level": "A-Level",
    "year": 2024,
    "paper": 1,
    "topics_covered": ["Organic Chemistry"],
    "questions": [
        {
            "question_number": "1",
            "question_text": "Study the reaction scheme below.",
            "topic": "Organic Chemistry",
            "subtopic": "Reaction Mechanisms",
            "marks_total": 12,
            "question_type": "Theory",
            "has_diagram": False,
            "has_figure": False,
            "has_subquestions": True,
            "image_url": None,
            "diagrams": [],
            "figures": [],
            "subquestions": [
                {
                    "subquestion_identifier": "a",
                    "text": "State the reagent used at step one.",
                    "marks": 2,
                    "image_url": None,
                    "sub_subquestions": [
                        {
                            "sub_subquestion_identifier": "iii",
                            "text": "Complete the table showing the products.",
                            "marks": 4,
                            "image_url": "https://example.com/table.png",
                        }
                    ],
                }
            ],
        }
    ],
}


def test_save_exam_persists_nested_subparts_with_images(client, mock_collections):
    mock_collections[
        "questions"
    ].where.return_value.where.return_value.stream.return_value = []

    # Metadata lookups (year/subject/topic) should appear not-yet-created
    for name in ["years", "subjects", "topics"]:
        mock_collections[name].document.return_value.get.return_value.exists = False

    # document().id must be a string so BaseRepository.create can build models
    for name, coll in mock_collections.items():
        coll.document.return_value.id = f"doc-{name}"

    response = client.post("/api/v1/exams/save", json=NESTED_EXAM)
    assert response.status_code == 200

    subquestion_calls = mock_collections["subquestions"].document().set.call_args_list
    assert len(subquestion_calls) == 1
    sq_payload = subquestion_calls[0][0][0]
    assert sq_payload["identifier"] == "a"
    assert "image_url" in sq_payload

    ssq_calls = mock_collections["sub_subquestions"].document().set.call_args_list
    assert len(ssq_calls) == 1
    ssq_payload = ssq_calls[0][0][0]
    assert ssq_payload["identifier"] == "iii"
    assert ssq_payload["subquestion_id"]  # reference to parent sub-question doc
    assert ssq_payload["image_url"] == "https://example.com/table.png"


def test_get_exam_returns_nested_subparts_with_images(client, mock_collections):
    mock_q_doc = MagicMock()
    mock_q_doc.id = "q1"
    mock_q_doc.to_dict.return_value = {
        "subject": "Chemistry",
        "year": 2024,
        "paper": 1,
        "question_number": "1",
        "question_text": "Study the reaction scheme below.",
        "topic": "Organic Chemistry",
        "subtopic": "Reaction Mechanisms",
        "marks_total": 12,
        "question_type": "Theory",
        "has_diagram": False,
        "has_figure": False,
        "has_subquestions": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    mock_collections[
        "questions"
    ].where.return_value.where.return_value.stream.return_value = [mock_q_doc]

    mock_sq_doc = MagicMock()
    mock_sq_doc.id = "sq1"
    mock_sq_doc.to_dict.return_value = {
        "question_id": "q1",
        "identifier": "a",
        "text": "State the reagent used at step one.",
        "marks": 2,
        "image_url": "https://example.com/step.png",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    mock_collections["subquestions"].where.return_value.stream.return_value = [
        mock_sq_doc
    ]

    mock_ssq_doc = MagicMock()
    mock_ssq_doc.id = "ssq1"
    mock_ssq_doc.to_dict.return_value = {
        "subquestion_id": "sq1",
        "identifier": "iii",
        "text": "Complete the table showing the products.",
        "marks": 4,
        "image_url": "https://example.com/table.png",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    mock_collections["sub_subquestions"].where.return_value.stream.return_value = [
        mock_ssq_doc
    ]

    mock_collections["diagrams"].where.return_value.stream.return_value = []
    mock_collections["figures"].where.return_value.stream.return_value = []

    mock_s_doc = MagicMock()
    mock_s_doc.id = "chemistry"
    mock_s_doc.exists = True
    mock_s_doc.to_dict.return_value = {"name": "Chemistry", "level": "A-Level"}
    mock_collections["subjects"].document.return_value.get.return_value = mock_s_doc

    response = client.get("/api/v1/exams/Chemistry/2024/1")
    assert response.status_code == 200
    data = response.json()

    q = data["questions"][0]
    assert q["question_number"] == "1"

    sq = q["subquestions"][0]
    assert sq["subquestion_identifier"] == "a"
    assert sq["image_url"] == "https://example.com/step.png"

    ssq = sq["sub_subquestions"][0]
    assert ssq["sub_subquestion_identifier"] == "iii"
    assert ssq["marks"] == 4
    assert ssq["image_url"] == "https://example.com/table.png"
