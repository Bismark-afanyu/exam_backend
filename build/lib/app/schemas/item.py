from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class BaseFirestoreSchema(BaseModel):
    id: Optional[str] = Field(None, alias="id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class Item(BaseFirestoreSchema):
    title: str
    description: Optional[str] = None
