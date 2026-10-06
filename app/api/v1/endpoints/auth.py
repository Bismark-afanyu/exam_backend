import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth as firebase_auth
from google.cloud.firestore import Client

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    verify_password,
    verify_reset_token,
)
from app.db.firebase import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.email import send_password_reset_email

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


@router.post("/forgot-password", status_code=200)
async def forgot_password(payload: ForgotPasswordRequest, db: Client = Depends(get_db)) -> dict[str, str]:
    """Sends a password reset link if the email exists. Always returns 200 to prevent enumeration."""
    repository = UserRepository(db)
    user = repository.get_by_email(payload.email)

    if user is not None:
        token = generate_reset_token(user["email"])
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        try:
            send_password_reset_email(user["email"], reset_link)
        except Exception:
            logger.exception("Failed to send reset email to %s", user["email"])

    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(payload: ResetPasswordRequest, db: Client = Depends(get_db)) -> dict[str, str]:
    """Resets a user's password using a valid reset token."""
    try:
        email = verify_reset_token(payload.token)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.") from e

    repository = UserRepository(db)
    user = repository.get_by_email(email)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    new_hash = hash_password(payload.new_password)
    repository.update_user(email, {"password_hash": new_hash})

    return {"message": "Password has been reset successfully."}
