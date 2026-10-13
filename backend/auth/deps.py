from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.db_models import User, AuthSession
from backend.security import (
    oauth2_scheme,
    extract_token_from_header,
    decode_access_token,
)


async def get_current_user_and_session(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Tuple[User, Optional[str]]:
    """
    Core dependency for authenticated requests.
    Validates JWT claims, checks server-side session revocation in AuthSession,
    and checks user token_version.
    """
    effective_token = token or extract_token_from_header(authorization)
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(effective_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated.",
        )

    # Validate token version (password changes, security resets)
    token_ver = payload.get("ver")
    if token_ver is not None and token_ver != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked due to a security update. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate server-side session status if sid is present in JWT
    session_id = payload.get("sid")
    if session_id:
        session_rec = db.query(AuthSession).filter(AuthSession.id == session_id).first()
        if not session_rec or session_rec.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user, session_id


async def get_authenticated_user(
    user_and_session: Tuple[User, Optional[str]] = Depends(get_current_user_and_session),
) -> User:
    """Convenience dependency returning User entity."""
    return user_and_session[0]


async def require_verified_user(
    user: User = Depends(get_authenticated_user),
) -> User:
    """Dependency verifying that account email address has been verified."""
    if not user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be verified before performing this action.",
        )
    return user
