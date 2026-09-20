from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import (
    DevImpersonateRequest,
    DevUserOut,
    LoginRequest,
    LoginResult,
    UserProfile,
)
from app.services import auth_service
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/wechat-login", response_model=LoginResult)
def wechat_login(payload: LoginRequest, db: DbSession) -> LoginResult:
    try:
        return auth_service.wechat_login(db, payload.code, payload.phone_code)
    except auth_service.PhoneRequiredError as exc:
        raise HTTPException(status_code=428, detail=str(exc))
    except auth_service.PhoneConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except auth_service.WeChatLoginError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.post("/dev-impersonate", response_model=LoginResult)
def dev_impersonate(payload: DevImpersonateRequest, db: DbSession) -> LoginResult:
    """Local-dev only: swap identity without going through WeChat.

    Rejected unless WECHAT_MOCK_LOGIN=true (never enabled in production).
    """
    try:
        return auth_service.dev_impersonate(db, payload.user_id)
    except auth_service.WeChatLoginError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        )


@router.get("/me", response_model=UserProfile)
def me(current_user: CurrentUser) -> UserProfile:
    return UserProfile.model_validate(current_user)


@router.get("/dev-users", response_model=list[DevUserOut])
def dev_users(db: DbSession) -> list[DevUserOut]:
    """Local-dev only: list identities for the dev switcher."""
    try:
        users = auth_service.list_dev_users(db)
    except auth_service.WeChatLoginError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    tree = load_org_tree(db)
    result: list[DevUserOut] = []
    for user in users:
        class_id = get_primary_class_id(db, user.id)
        org_path = tree.path_name(class_id) if class_id else ""
        result.append(
            DevUserOut(id=user.id, name=user.name, role=user.role, org_path=org_path)
        )
    return result
