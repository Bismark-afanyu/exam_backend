"""Firestore-backed community posts and comments.

Posts live in `community_posts`; comments are a subcollection per post
(`community_posts/{id}/comments`). Likes are stored as a `liked_by`
array with an atomic `like_count` increment, so a like never needs a
transaction.
"""

from datetime import UTC, datetime

from google.cloud import firestore
from google.cloud.firestore import Client
from google.cloud.firestore_v1.base_query import FieldFilter

POSTS_COLLECTION = "community_posts"


class CommunityRepository:
    def __init__(self, db: Client):
        self.db = db
        self.posts = db.collection(POSTS_COLLECTION)

    # ----- posts -----

    def create_post(
        self, author_id: str, author_name: str, data: dict
    ) -> dict:
        doc_ref = self.posts.document()
        payload = {
            **data,
            "author_id": author_id,
            "author_name": author_name,
            "like_count": 0,
            "comment_count": 0,
            "liked_by": [],
            "created_at": datetime.now(UTC),
        }
        doc_ref.set(payload)
        return {**payload, "id": doc_ref.id}

    def list_posts(
        self, limit: int = 20, cursor: datetime | None = None
    ) -> list[dict]:
        """Newest-first page of posts. `cursor` is the created_at of the
        last post of the previous page."""
        query = self.posts.order_by("created_at", direction="DESCENDING")
        if cursor is not None:
            query = query.where(
                filter=FieldFilter("created_at", "<", cursor)
            )
        docs = query.limit(limit).stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]

    def get_post(self, post_id: str) -> dict | None:
        doc = self.posts.document(post_id).get()
        if not doc.exists:
            return None
        return {**doc.to_dict(), "id": doc.id}

    def delete_post(self, post_id: str) -> bool:
        ref = self.posts.document(post_id)
        if not ref.get().exists:
            return False
        for comment in ref.collection("comments").stream():
            comment.reference.delete()
        ref.delete()
        return True

    def toggle_like(self, post_id: str, user_id: str) -> bool | None:
        """Likes/unlikes on behalf of a user. Returns the new liked state,
        or None when the post does not exist."""
        ref = self.posts.document(post_id)
        snap = ref.get()
        if not snap.exists:
            return None
        liked = user_id in (snap.to_dict() or {}).get("liked_by", [])
        if liked:
            ref.update(
                {
                    "liked_by": firestore.ArrayRemove([user_id]),
                    "like_count": firestore.Increment(-1),
                }
            )
        else:
            ref.update(
                {
                    "liked_by": firestore.ArrayUnion([user_id]),
                    "like_count": firestore.Increment(1),
                }
            )
        return not liked

    def stats(self) -> dict:
        posts_count = 0
        comments_count = 0
        try:
            posts_snapshot = self.posts.count().get()
            comments_snapshot = self.posts.sum("comment_count").get()
            posts_count = int(posts_snapshot[0][0].value or 0)
            comments_count = int(comments_snapshot[0][0].value or 0)
        except Exception:
            # Aggregation queries need a recent Firestore runtime; fall
            # back to a plain stream for small archives.
            for doc in self.posts.stream():
                posts_count += 1
                comments_count += int(
                    (doc.to_dict() or {}).get("comment_count", 0)
                )
        return {"posts": posts_count, "comments": comments_count}

    # ----- comments -----

    def add_comment(
        self, post_id: str, author_id: str, author_name: str, content: str
    ) -> dict | None:
        post_ref = self.posts.document(post_id)
        if not post_ref.get().exists:
            return None
        payload = {
            "author_id": author_id,
            "author_name": author_name,
            "content": content,
            "created_at": datetime.now(UTC),
        }
        comment_ref = post_ref.collection("comments").document()
        comment_ref.set(payload)
        post_ref.update(
            {"comment_count": firestore.Increment(1)}
        )
        return {**payload, "id": comment_ref.id, "post_id": post_id}

    def list_comments(self, post_id: str) -> list[dict] | None:
        ref = self.posts.document(post_id)
        if not ref.get().exists:
            return None
        docs = (
            ref.collection("comments")
            .order_by("created_at", direction="ASCENDING")
            .stream()
        )
        return [
            {**doc.to_dict(), "id": doc.id, "post_id": post_id}
            for doc in docs
        ]
