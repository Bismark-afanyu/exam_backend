"""Community posts/comments integration tests against mocked Firestore."""

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
    get_collection("community_posts")
    return collections


def _post_doc(post_id="post1", author="student@example.com", **overrides):
    data = {
        "author_id": author,
        "author_name": "Test Student",
        "title": "How do I balance redox equations?",
        "content": "I keep failing the oxygen part. Any tricks?",
        "post_type": "question",
        "subject": "Chemistry",
        "like_count": 3,
        "comment_count": 1,
        "liked_by": ["other@example.com"],
        "created_at": "2026-10-05T10:00:00+00:00",
    }
    data.update(overrides)
    doc = MagicMock()
    doc.id = post_id
    doc.to_dict.return_value = data
    return doc


SAMPLE_POST = {
    "title": "How do I balance redox equations?",
    "content": "I keep failing the oxygen part. Any tricks?",
    "post_type": "question",
    "subject": "Chemistry",
}


def test_create_post_returns_post_with_liked_by_me_false(client, mock_collections):
    mock_collections["community_posts"].document.return_value.id = "post1"

    response = client.post("/api/v1/community/posts", json=SAMPLE_POST)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "post1"
    assert data["author_name"] == "Test Student"
    assert data["liked_by_me"] is False
    assert data["like_count"] == 0
    assert data["comment_count"] == 0


def test_list_posts_marks_liked_by_me(client, mock_collections):
    mock_collections[
        "community_posts"
    ].order_by.return_value.limit.return_value.stream.return_value = [
        _post_doc(post_id="p1", author="test@example.com", liked_by=["test@example.com"]),
    ]

    response = client.get("/api/v1/community/posts")

    assert response.status_code == 200
    posts = response.json()
    assert len(posts) == 1
    # The test user IS the author of this post and liked it themselves.
    assert posts[0]["liked_by_me"] is True


def test_toggle_like_unlikes_when_already_liked(client, mock_collections):
    posts = mock_collections["community_posts"]
    first_snap = MagicMock()
    first_snap.exists = True
    first_snap.to_dict.return_value = {
        "liked_by": ["test@example.com"],
        "like_count": 4,
    }
    second_snap = MagicMock()
    second_snap.exists = True
    second_snap.to_dict.return_value = {"liked_by": [], "like_count": 3}
    # First read = toggle check, second read = fresh count for the response.
    posts.document.return_value.get.side_effect = [first_snap, second_snap]

    response = client.post("/api/v1/community/posts/post1/like")

    assert response.status_code == 200
    data = response.json()
    assert data["liked"] is False
    assert data["like_count"] == 3
    update_args = posts.document.return_value.update.call_args[0][0]
    assert update_args["like_count"].value == -1


def test_toggle_like_404_for_missing_post(client, mock_collections):
    snap = MagicMock()
    snap.exists = False
    mock_collections["community_posts"].document.return_value.get.return_value = snap

    response = client.post("/api/v1/community/posts/missing/like")

    assert response.status_code == 404


def test_add_comment_increments_count(client, mock_collections):
    posts = mock_collections["community_posts"]
    post_snap = MagicMock()
    post_snap.exists = True
    posts.document.return_value.get.return_value = post_snap
    comment_doc = posts.document.return_value.collection.return_value.document
    comment_doc.return_value.id = "c1"

    response = client.post(
        "/api/v1/community/posts/post1/comments",
        json={"content": "Balance oxygen with water, then hydrogen with H+."},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "c1"
    assert data["post_id"] == "post1"
    assert data["author_name"] == "Test Student"
    update_args = posts.document.return_value.update.call_args[0][0]
    assert update_args["comment_count"].value == 1


def test_list_comments_404_for_missing_post(client, mock_collections):
    snap = MagicMock()
    snap.exists = False
    mock_collections["community_posts"].document.return_value.get.return_value = snap

    response = client.get("/api/v1/community/posts/missing/comments")

    assert response.status_code == 404


def test_delete_post_denied_for_non_author(client, mock_collections):
    snap = MagicMock()
    snap.exists = True
    snap.to_dict.return_value = _post_doc(post_id="p1", author="someone@else.com").to_dict.return_value
    mock_collections["community_posts"].document.return_value.get.return_value = snap

    response = client.delete("/api/v1/community/posts/p1")

    assert response.status_code == 403


def test_delete_post_allowed_for_author(client, mock_collections):
    snap = MagicMock()
    snap.exists = True
    snap.to_dict.return_value = _post_doc(post_id="p1", author="test@example.com").to_dict.return_value
    mock_collections["community_posts"].document.return_value.get.return_value = snap
    # comments subcollection is empty
    mock_collections["community_posts"].document.return_value.collection.return_value.stream.return_value = []

    response = client.delete("/api/v1/community/posts/p1")

    assert response.status_code == 204
    mock_collections["community_posts"].document.return_value.delete.assert_called_once()


def test_community_requires_auth(mock_db):
    from fastapi.testclient import TestClient

    from app.db.firebase import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        response = c.get("/api/v1/community/posts")
    app.dependency_overrides = {}
    assert response.status_code == 401


def test_stats_returns_counts(client, mock_collections):
    class _AggValue:
        value = 7

        def __getitem__(self, _index):
            return self

    class _AggSnapshot:
        def __getitem__(self, _index):
            return _AggValue()

    mock_collections[
        "community_posts"
    ].count.return_value.get.return_value = _AggSnapshot()
    mock_collections[
        "community_posts"
    ].sum.return_value.get.return_value = _AggSnapshot()

    response = client.get("/api/v1/community/stats")

    assert response.status_code == 200
    assert response.json() == {"posts": 7, "comments": 7}
