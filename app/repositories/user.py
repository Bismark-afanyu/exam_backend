from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import Client

from app.schemas.auth import UserCreate, UserRead


class UserRepository:
    """Repository for the Firestore `users` collection, keyed by email."""

    COLLECTION = "users"

    def __init__(self, db: Client):
        self.db = db
        self.collection = db.collection(self.COLLECTION)

    @staticmethod
    def _doc_id(email: str) -> str:
        return email.strip().lower()

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        doc = self.collection.document(self._doc_id(email)).get()
        if not doc.exists:
            return None
        return {**doc.to_dict(), "id": doc.id}

    def exists(self, email: str) -> bool:
        return self.collection.document(self._doc_id(email)).get().exists

    def create(self, data: UserCreate, password_hash: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc_ref = self.collection.document(self._doc_id(data.email))
        payload = {
            "full_name": data.full_name.strip(),
            "email": self._doc_id(data.email),
            "password_hash": password_hash,
            "role": "student",
            "created_at": now,
            "updated_at": now,
        }
        doc_ref.set(payload)
        return {**payload, "id": doc_ref.id}

    def get_or_create_google_user(
        self,
        email: str,
        full_name: str,
        google_uid: str,
        picture_url: str | None = None,
    ) -> dict[str, Any]:
        """Finds a user by email, creating it (or linking a Google identity)
        when it does not exist yet. Returns the stored user document."""
        now = datetime.now(UTC)
        doc_ref = self.collection.document(self._doc_id(email))
        existing = doc_ref.get()

        if existing.exists:
            updates: dict[str, Any] = {"updated_at": now}
            data = existing.to_dict()
            if not data.get("google_uid"):
                updates["google_uid"] = google_uid
            if picture_url and not data.get("picture_url"):
                updates["picture_url"] = picture_url
            if updates != {"updated_at": now}:
                doc_ref.update(updates)
            return {**data, **updates, "id": doc_ref.id}

        payload = {
            "full_name": full_name.strip() or "Google User",
            "email": self._doc_id(email),
            "google_uid": google_uid,
            "picture_url": picture_url,
            "role": "student",
            "created_at": now,
            "updated_at": now,
        }
        doc_ref.set(payload)
        return {**payload, "id": doc_ref.id}

    def to_user_read(self, user: dict[str, Any]) -> UserRead:
        return UserRead(
            id=user["id"],
            full_name=user.get("full_name", ""),
            email=user.get("email", ""),
            role=user.get("role", "student"),
            created_at=user.get("created_at"),
        )

    def list_team_members(self) -> list[dict[str, Any]]:
        """Lists all users with an 'admin' or 'editor' role."""
        docs = self.collection.where("role", "in", ["admin", "editor"]).stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]

    def create_team_member(self, data, password_hash: str) -> dict[str, Any]:
        """Creates a team member (admin/editor) account keyed by email."""
        now = datetime.now(UTC)
        doc_ref = self.collection.document(self._doc_id(data.email))
        payload = {
            "full_name": data.full_name.strip(),
            "email": self._doc_id(data.email),
            "password_hash": password_hash,
            "role": data.role,
            "created_at": now,
            "updated_at": now,
        }
        doc_ref.set(payload)
        return {**payload, "id": doc_ref.id}

    def update_user(self, email: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Updates a user document by email. Returns the updated user or None."""
        doc_ref = self.collection.document(self._doc_id(email))
        if not doc_ref.get().exists:
            return None
        updates["updated_at"] = datetime.now(UTC)
        doc_ref.update(updates)
        updated = doc_ref.get().to_dict()
        return {**updated, "id": doc_ref.id}

    def delete_by_email(self, email: str) -> bool:
        """Deletes a user document by email. Returns True if it existed."""
        doc_ref = self.collection.document(self._doc_id(email))
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        return True
