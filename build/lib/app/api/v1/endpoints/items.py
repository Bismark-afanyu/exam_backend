from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.db.firebase import get_db
from app.schemas.item import Item, ItemCreate, ItemUpdate
from datetime import datetime
from google.cloud.firestore import Client

router = APIRouter()

COLLECTION_NAME = "items"

@router.post("/", response_model=Item, status_code=201)
async def create_item(item_in: ItemCreate, db: Client = Depends(get_db)):
    item_dict = item_in.model_dump()
    item_dict["created_at"] = datetime.utcnow()
    item_dict["updated_at"] = datetime.utcnow()
    
    doc_ref = db.collection(COLLECTION_NAME).document()
    doc_ref.set(item_dict)
    
    return {**item_dict, "id": doc_ref.id}

@router.get("/", response_model=List[Item])
async def read_items(db: Client = Depends(get_db)):
    docs = db.collection(COLLECTION_NAME).stream()
    items = []
    for doc in docs:
        items.append({**doc.to_dict(), "id": doc.id})
    return items

@router.get("/{item_id}", response_model=Item)
async def read_item(item_id: str, db: Client = Depends(get_db)):
    doc = db.collection(COLLECTION_NAME).document(item_id).get()
    if not doc.exists:
        raise HTTPException(status_ID=404, detail="Item not found")
    return {**doc.to_dict(), "id": doc.id}

@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: str, item_in: ItemUpdate, db: Client = Depends(get_db)):
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    doc_ref.update(update_data)
    
    updated_doc = doc_ref.get()
    return {**updated_doc.to_dict(), "id": updated_doc.id}

@router.delete("/{item_id}")
async def delete_item(item_id: str, db: Client = Depends(get_db)):
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Item not found")
    doc_ref.delete()
    return {"message": "Item deleted successfully"}
