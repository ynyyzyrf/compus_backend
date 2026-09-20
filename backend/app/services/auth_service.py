"""WeChat login.

Production: exchange the wx.login() code for openid via jscode2session.
Dev (WECHAT_MOCK_LOGIN=true): skip the WeChat API (no AppSecret locally) and
resolve to the seeded super admin; /auth/dev-impersonate switches identities.
"""

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.enums import Role, Status
from app.models.user import User

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


class WeChatLoginError(Exception):
    pass


def _issue(user: User) -> dict:
    token = create_access_token(user.id, user.role)
    return {"access_token": token, "token_type": "Bearer", "user": user}


def _code2session(code: str) -> tuple[str, str | None]:
    params = {
        "appid": settings.wechat_appid,
        "secret": settings.wechat_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    try:
        resp = httpx.get(JSCODE2SESSION_URL, params=params, timeout=8)
        data = resp.json()
    except Exception as exc:  # network / JSON failure
        raise WeChatLoginError("微信登錄服務暫不可用") from exc

    if data.get("errcode"):
        raise WeChatLoginError(
            f"微信登錄失敗: {data.get('errmsg', data['errcode'])}"
        )
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
    user = db.scalars(select(User).where(User.openid == openid)).first()
    if user is None:
        # First login: create a basic profile, completed later by the user.
        user = User(
            openid=openid,
            unionid=unionid,
            name="未命名校友",
            role=Role.USER,
            status=Status.ACTIVE,
        )
        db.add(user)
        db.commit()
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
