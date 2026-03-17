from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from google.cloud.firestore import Client
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T", bound=BaseModel)

class BaseRepository(Generic[T]):
    """Generic CRUD repository for Firestore collections."""
    
    def __init__(self, db: Client, model_class: Type[T], collection_name: str):
        self.db = db
        self.model_class = model_class
        self.collection_name = collection_name
        self.collection = self.db.collection(self.collection_name)

    def get(self, doc_id: str) -> Optional[T]:
        doc = self.collection.document(doc_id).get()
        if doc.exists:
            return self.model_class(**{**doc.to_dict(), "id": doc.id})
        return None

    def get_by_field(self, field: str, value: Any) -> List[T]:
        docs = self.collection.where(field, "==", value).stream()
        return [self.model_class(**{**doc.to_dict(), "id": doc.id}) for doc in docs]

    def create(self, data: T, doc_id: Optional[str] = None) -> T:
        data_dict = data.model_dump(exclude={"id"}, exclude_unset=True)
        if "created_at" in data_dict and not data_dict.get("created_at"):
            data_dict["created_at"] = datetime.utcnow()
        if "updated_at" in data_dict and not data_dict.get("updated_at"):
            data_dict["updated_at"] = datetime.utcnow()

        if doc_id:
            doc_ref = self.collection.document(doc_id)
            doc_ref.set(data_dict)
        else:
            doc_ref = self.collection.document()
            doc_ref.set(data_dict)
            
        return self.model_class(**{**data_dict, "id": doc_ref.id})

    def update(self, doc_id: str, data: Dict[str, Any]) -> Optional[T]:
        doc_ref = self.collection.document(doc_id)
        if not doc_ref.get().exists:
            return None
            
        data["updated_at"] = datetime.utcnow()
        doc_ref.update(data)
        
        updated_doc = doc_ref.get()
        return self.model_class(**{**updated_doc.to_dict(), "id": updated_doc.id})

    def delete(self, doc_id: str) -> bool:
        doc_ref = self.collection.document(doc_id)
        if doc_ref.get().exists:
            doc_ref.delete()
            return True
        return False

    def list_all(self) -> List[T]:
        docs = self.collection.stream()
        return [self.model_class(**{**doc.to_dict(), "id": doc.id}) for doc in docs]
