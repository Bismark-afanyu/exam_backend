from datetime import UTC, datetime

from pydantic import BaseModel, Field


class BaseFirestoreSchema(BaseModel):
    id: str | None = Field(None, alias="id")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ItemCreate(BaseModel):
    title: str
    description: str | None = None


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class Item(BaseFirestoreSchema):
    title: str
    description: str | None = None
