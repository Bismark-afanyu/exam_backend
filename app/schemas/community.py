from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

POST_TYPE = Literal["question", "discussion"]
POST_TYPES = ("question", "discussion")


class CommunityPostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    content: str = Field(min_length=1, max_length=2000)
    post_type: POST_TYPE = "discussion"
    subject: str | None = Field(default=None, max_length=100)


class CommunityPostRead(BaseModel):
    id: str
    author_id: str
    author_name: str
    title: str
    content: str
    post_type: str
    subject: str | None = None
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False
    created_at: datetime | None = None


class CommunityCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class CommunityCommentRead(BaseModel):
    id: str
    post_id: str
    author_id: str
    author_name: str
    content: str
    created_at: datetime | None = None


class CommunityStats(BaseModel):
    posts: int
    comments: int


class CommunityLikeResult(BaseModel):
    liked: bool
    like_count: int
