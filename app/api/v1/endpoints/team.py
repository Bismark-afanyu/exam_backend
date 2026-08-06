from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import Client

from app.api.deps import get_current_admin
from app.core.security import hash_password
from app.db.firebase import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import UserRead
from app.schemas.team import TeamMemberCreate, TeamMemberUpdate

router = APIRouter()


@router.get("/members", response_model=list[UserRead])
async def list_team_members(
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_admin),
) -> list[UserRead]:
    """Lists all team member accounts (admins and editors)."""
    repository = UserRepository(db)
    members = repository.list_team_members()
    return [UserRead(**{**m, "id": m["id"]}) for m in members]


@router.post("/members", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    payload: TeamMemberCreate,
    db: Client = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_admin),
) -> UserRead:
    """Creates an admin/editor account (an invite)."""
    repository = UserRepository(db)
    if repository.exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team member with this email already exists.",
        )

    password_hash = hash_password(payload.password)
    user = repository.create_team_member(payload, password_hash)
    return UserRead(**user)


@router.patch("/members/{email}", response_model=UserRead)
async def update_team_member(
    email: str,
    payload: TeamMemberUpdate,
    db: Client = Depends(get_db),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> UserRead:
    """Updates a team member's name, role, or password."""
    repository = UserRepository(db)
    member = repository.get_by_email(email)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found.",
        )

    if (
        email.strip().lower() == current_admin.get("email", "")
        and payload.role is not None
        and payload.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role.",
        )

    updates: dict[str, Any] = {}
    if payload.full_name is not None:
        updates["full_name"] = payload.full_name.strip()
    if payload.role is not None:
        updates["role"] = payload.role
    if payload.password is not None:
        updates["password_hash"] = hash_password(payload.password)

    if not updates:
        return UserRead(**{**member, "id": member["id"]})

    updated = repository.update_user(email, updates)
    return UserRead(**updated)


@router.delete("/members/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_member(
    email: str,
    db: Client = Depends(get_db),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> None:
    """Removes a team member account."""
    if email.strip().lower() == current_admin.get("email", ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own account.",
        )

    repository = UserRepository(db)
    if not repository.delete_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found.",
        )
