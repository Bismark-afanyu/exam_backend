from unittest.mock import MagicMock

from tests.factories.item_factory import ItemCreateFactory


def test_create_item(client, mock_db):
    item_in = ItemCreateFactory()
    
    # Mocking the Firestore create logic
    mock_doc = MagicMock()
    mock_doc.id = "test_id"
    mock_db.collection.return_value.document.return_value = mock_doc
    
    response = client.post("/api/v1/items/", json=item_in.model_dump())
    
    assert response.status_code == 201
    assert response.json()["title"] == item_in.title
    assert response.json()["id"] == "test_id"

def test_read_items(client, mock_db):
    # Mocking the Firestore read logic
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {"title": "Test Item", "description": "Desc"}
    mock_doc.id = "test_id"
    mock_db.collection.return_value.stream.return_value = [mock_doc]
    
    response = client.get("/api/v1/items/")
    
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert response.json()[0]["title"] == "Test Item"
