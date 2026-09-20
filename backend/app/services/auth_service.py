"""WeChat Mini Program login keyed by the current AppID's openid."""

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.enums import Role, Status
from app.models.user import User

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WeChatLoginError(Exception):
    pass


class AccountUnavailableError(WeChatLoginError):
    pass


def _issue(user: User) -> dict:
    token = create_access_token(user.id, user.role, user.auth_version)
    return {"access_token": token, "token_type": "Bearer", "user": user}


def _code2session(code: str) -> tuple[str, str | None]:
    params = {
        "appid": settings.wechat_appid,
        "secret": settings.wechat_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        data = httpx.get(JSCODE2SESSION_URL, params=params, timeout=8).json()
    except Exception as exc:
        raise WeChatLoginError("微信登錄服務暫不可用") from exc
    if data.get("errcode"):
        raise WeChatLoginError(f"微信登錄失敗: {data.get('errmsg', data['errcode'])}")
    if not data.get("openid"):
        raise WeChatLoginError("微信未返回用戶身份")
    return data["openid"], data.get("unionid")


def wechat_login(db: Session, code: str) -> dict:
    if settings.wechat_mock_login:
        user = db.scalars(
            select(User)
            .where(User.role == Role.SUPER_ADMIN, User.status == Status.ACTIVE)
            .order_by(User.id)
            .limit(1)
        ).first()
        if user is None:
            raise WeChatLoginError("開發庫缺少種子超管，請先執行 seed_dev")
        return _issue(user)

    openid, unionid = _code2session(code)
    current = db.scalars(
        select(User).where(User.openid == openid).with_for_update()
    ).first()
    if current:
        if current.status != Status.ACTIVE:
            raise AccountUnavailableError("用戶已停用，請聯絡管理員")
        return _issue(current)

    user = User(
        openid=openid, unionid=unionid, name="未命名校友",
        role=Role.USER, status=Status.ACTIVE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent login may have inserted the same unique openid.
        db.rollback()
        user = db.scalars(select(User).where(User.openid == openid)).first()
        if user is None:
            raise WeChatLoginError("微信身份建立失敗，請重試")
        if user.status != Status.ACTIVE:
            raise AccountUnavailableError("用戶已停用，請聯絡管理員")
        return _issue(user)
    db.refresh(user)
    return _issue(user)


def dev_impersonate(db: Session, user_id: int) -> dict:
    if not settings.wechat_mock_login:
        raise WeChatLoginError("dev-impersonate 僅在 WECHAT_MOCK_LOGIN=true 時可用")
    user = db.get(User, user_id)
    if user is None or user.status != Status.ACTIVE:
        raise WeChatLoginError("目標用戶不存在或已停用")
    return _issue(user)


def list_dev_users(db: Session) -> list[User]:
    if not settings.wechat_mock_login:
        raise WeChatLoginError("僅開發模式可用")
    return list(db.scalars(select(User).order_by(User.id)))
