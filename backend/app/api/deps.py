from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmergencyProtectionSetting, User
from app.services.security import decode_token

bearer = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sign in to continue.",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR
    payload = decode_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise CREDENTIALS_ERROR
    user = db.scalar(select(User).where(User.email == payload["sub"]))
    if user is None:
        raise CREDENTIALS_ERROR
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="This area is limited to admin accounts."
        )
    return user


def protection_for(db: Session, user: User) -> EmergencyProtectionSetting:
    setting = db.scalar(
        select(EmergencyProtectionSetting).where(EmergencyProtectionSetting.user_id == user.id)
    )
    if setting is None:
        setting = EmergencyProtectionSetting(user_id=user.id)
        db.add(setting)
        db.flush()
    return setting
