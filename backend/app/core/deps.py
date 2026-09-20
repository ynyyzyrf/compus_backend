from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import Role, Status
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="未登錄"
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["uid"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登錄已過期，請重新登錄"
        )

    user = db.get(User, user_id)
    if user is None or user.status != Status.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用戶不可用"
        )
    if payload.get("ver", 0) != user.auth_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="登錄已過期，請重新登錄"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_super_admin(user: CurrentUser) -> User:
    if user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要超級管理員權限"
        )
    return user


SuperAdmin = Annotated[User, Depends(require_super_admin)]
