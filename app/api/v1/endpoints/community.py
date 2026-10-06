import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud.firestore import Client

from app.api.deps import get_current_user
from app.db.firebase import get_db
from app.repositories.community import CommunityRepository
from app.schemas.community import (
    CommunityCommentCreate,
    CommunityCommentRead,
    CommunityLikeResult,
    CommunityPostCreate,
    CommunityPostRead,
    CommunityStats,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _post_read(post: dict[str, Any], user_id: str) -> CommunityPostRead:
    return CommunityPostRead(
        id=post["id"],
        author_id=post.get("author_id", ""),
        author_name=post.get("author_name", "Anonymous"),
        title=post.get("title", ""),
        content=post.get("content", ""),
        post_type=post.get("post_type", "discussion"),
        subject=post.get("subject"),
        like_count=post.get("like_count", 0),
        comment_count=post.get("comment_count", 0),
        liked_by_me=user_id in post.get("liked_by", []),
        created_at=post.get("created_at"),
    )


def _comment_read(comment: dict[str, Any]) -> CommunityCommentRead:
    return CommunityCommentRead(
        id=comment["id"],
        post_id=comment.get("post_id", ""),
        author_id=comment.get("author_id", ""),
        author_name=comment.get("author_name", "Anonymous"),
        content=comment.get("content", ""),
        created_at=comment.get("created_at"),
    )


@router.get("/posts", response_model=list[CommunityPostRead])
async def list_posts(
    limit: int = Query(default=20, ge=1, le=50),
    cursor: datetime | None = None,
    db: Client = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
):
    """Newest community posts. Pass the last post's created_at as `cursor`
    to fetch the next page."""
    try:
        repository = CommunityRepository(db)
        posts = repository.list_posts(limit=limit, cursor=cursor)
        return [_post_read(post, user["id"]) for post in posts]
    except Exception:
        logger.error("Failed to list community posts", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error listing community posts."
        ) from None


@router.post("/posts", response_model=CommunityPostRead, status_code=201)
async def create_post(
    post_in: CommunityPostCreate,
    db: Client = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
):
    try:
        repository = CommunityRepository(db)
        post = repository.create_post(
            author_id=user["id"],
            author_name=user.get("full_name") or "Anonymous",
            data=post_in.model_dump(exclude_unset=True),
        )
        return _post_read(post, user["id"])
    except Exception:
        logger.error("Failed to create community post", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error creating post."
        ) from None


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: str,
    db: Client = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
):
    """Authors delete their own posts; admins can delete any post."""
    repository = CommunityRepository(db)
    post = repository.get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("author_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(
            status_code=403, detail="You can only delete your own posts."
        )
    repository.delete_post(post_id)


@router.post("/posts/{post_id}/like", response_model=CommunityLikeResult)
async def toggle_like(
    post_id: str,
    db: Client = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
):
    try:
        repository = CommunityRepository(db)
        result = repository.toggle_like(post_id, user["id"])
        if result is None:
            raise HTTPException(status_code=404, detail="Post not found")
        post = repository.get_post(post_id)
        return CommunityLikeResult(
            liked=result,
            like_count=(post or {}).get("like_count", 0),
        )
    except HTTPException:
        raise
    except Exception:
        logger.error(f"Failed to toggle like on post {post_id}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error updating like."
        ) from None


@router.get(
    "/posts/{post_id}/comments", response_model=list[CommunityCommentRead]
)
async def list_comments(
    post_id: str,
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
):
    try:
        repository = CommunityRepository(db)
        comments = repository.list_comments(post_id)
        if comments is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return [_comment_read(comment) for comment in comments]
    except HTTPException:
        raise
    except Exception:
        logger.error(f"Failed to list comments for post {post_id}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error listing comments."
        ) from None


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommunityCommentRead,
    status_code=201,
)
async def add_comment(
    post_id: str,
    comment_in: CommunityCommentCreate,
    db: Client = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
):
    try:
        repository = CommunityRepository(db)
        comment = repository.add_comment(
            post_id=post_id,
            author_id=user["id"],
            author_name=user.get("full_name") or "Anonymous",
            content=comment_in.content,
        )
        if comment is None:
            raise HTTPException(status_code=404, detail="Post not found")
        return _comment_read(comment)
    except HTTPException:
        raise
    except Exception:
        logger.error(f"Failed to add comment to post {post_id}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error adding comment."
        ) from None


@router.get("/stats", response_model=CommunityStats)
async def community_stats(
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
):
    try:
        repository = CommunityRepository(db)
        return CommunityStats(**repository.stats())
    except Exception:
        logger.error("Failed to read community stats", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error reading community stats."
        ) from None
