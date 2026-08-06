from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from google.cloud.firestore import Client

from app.core.security import decode_token
from app.db.firebase import get_db
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Client = Depends(get_db),
) -> dict[str, Any]:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise CREDENTIALS_EXCEPTION from e

    user_id = payload.get("sub")
    if not user_id:
        raise CREDENTIALS_EXCEPTION

    user = UserRepository(db).get_by_email(user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION

    return user


def get_current_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Requires an authenticated user with the 'admin' role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return user
