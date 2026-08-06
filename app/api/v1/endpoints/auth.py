import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth as firebase_auth
from google.cloud.firestore import Client

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.firebase import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import (
    GoogleAuthRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=201)
async def register(
    user_in: UserCreate, db: Client = Depends(get_db)
) -> dict[str, Any]:
    repository = UserRepository(db)

    if repository.exists(user_in.email):
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    password_hash = hash_password(user_in.password)
    user = repository.create(user_in, password_hash)

    token = create_access_token(subject=user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserRead(**user).model_dump(),
    }


@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin, db: Client = Depends(get_db)
) -> dict[str, Any]:
    repository = UserRepository(db)
    user = repository.get_by_email(user_in.email)

    if user is None or not verify_password(
        user_in.password, user.get("password_hash", "")
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
        )

    token = create_access_token(subject=user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserRead(**user).model_dump(),
    }


@router.post("/google", response_model=Token)
async def google_auth(
    payload: GoogleAuthRequest, db: Client = Depends(get_db)
) -> dict[str, Any]:
    """Authenticates a user with a Google ID token from Firebase Auth.

    The token is verified by Firebase and the user is created on first sign-in
    (or linked to an existing account with the same email).
    """
    try:
        decoded = firebase_auth.verify_id_token(payload.id_token)
    except Exception as e:
        logger.warning("Invalid Google ID token: %s", e)
        raise HTTPException(
            status_code=401, detail="Invalid Google credentials."
        ) from e

    email = (decoded.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Your Google account has no email address.",
        )

    repository = UserRepository(db)
    user = repository.get_or_create_google_user(
        email=email,
        full_name=decoded.get("name", "") or "",
        google_uid=decoded.get("uid", ""),
        picture_url=decoded.get("picture"),
    )

    token = create_access_token(subject=user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserRead(**user).model_dump(),
    }


@router.get("/me", response_model=UserRead)
async def read_me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserRead:
    return UserRead(
        id=current_user["id"],
        full_name=current_user.get("full_name", ""),
        email=current_user.get("email", ""),
        role=current_user.get("role", "student"),
        created_at=current_user.get("created_at"),
    )
