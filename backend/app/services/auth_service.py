"""WeChat login and verified phone binding."""

from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.activity import Activity, ActivityCheckin, ActivitySignup, Photo
from app.models.content import Article
from app.models.enums import Role, SignupStatus, Status
from app.models.organization import Membership
from app.models.relay import Relay, RelayResponse
from app.models.user import User

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
PHONE_NUMBER_URL = "https://api.weixin.qq.com/wxa/business/getuserphonenumber"

_token_lock = Lock()
_access_token_value = ""
_access_token_expires_at = 0.0


class WeChatLoginError(Exception):
    pass


class PhoneRequiredError(WeChatLoginError):
    pass


class PhoneConflictError(WeChatLoginError):
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


def _access_token() -> str:
    global _access_token_value, _access_token_expires_at
    with _token_lock:
        if _access_token_value and monotonic() < _access_token_expires_at:
            return _access_token_value
        try:
            data = httpx.get(
                ACCESS_TOKEN_URL,
                params={
                    "grant_type": "client_credential",
                    "appid": settings.wechat_appid,
                    "secret": settings.wechat_secret,
                },
                timeout=8,
            ).json()
        except Exception as exc:
            raise WeChatLoginError("微信手機號服務暫不可用") from exc
        token = data.get("access_token")
        if not token:
            raise WeChatLoginError(
                f"獲取微信接口憑證失敗: {data.get('errmsg', data.get('errcode', 'unknown'))}"
            )
        _access_token_value = token
        _access_token_expires_at = monotonic() + max(int(data.get("expires_in", 7200)) - 120, 1)
        return token


def _get_phone(phone_code: str) -> tuple[str, str]:
    """Return (E.164-like identity, local digits) from a one-use WeChat code."""
    try:
        data = httpx.post(
            PHONE_NUMBER_URL,
            params={"access_token": _access_token()},
            json={"code": phone_code},
            timeout=8,
        ).json()
    except Exception as exc:
        raise WeChatLoginError("微信手機號服務暫不可用") from exc
    if data.get("errcode"):
        raise WeChatLoginError(
            f"手機號授權失敗: {data.get('errmsg', data['errcode'])}"
        )
    info = data.get("phone_info") or {}
    country = str(info.get("countryCode") or "")
    local = str(info.get("purePhoneNumber") or "")
    watermark = info.get("watermark") or {}
    if (
        not country.isdigit()
        or not local.isdigit()
        or not 6 <= len(local) <= 20
        or watermark.get("appid") != settings.wechat_appid
    ):
        raise WeChatLoginError("微信手機號資料無效")
    return f"+{country}{local}", local


def _merge_unique_user_rows(db: Session, model, scope_field: str, source: User, target: User) -> None:
    target_rows = {
        getattr(row, scope_field): row
        for row in db.scalars(select(model).where(model.user_id == target.id))
    }
    to_move = []
    for row in db.scalars(select(model).where(model.user_id == source.id)):
        existing = target_rows.get(getattr(row, scope_field))
        if existing is not None:
            if model is ActivitySignup:
                if row.status == SignupStatus.SIGNED:
                    existing.status = SignupStatus.SIGNED
                existing.phone = existing.phone or row.phone
                existing.remark = existing.remark or row.remark
                db.execute(
                    update(ActivityCheckin)
                    .where(ActivityCheckin.signup_id == row.id)
                    .values(signup_id=existing.id)
                )
            elif model is Membership:
                existing.is_primary = existing.is_primary or row.is_primary
            elif model is RelayResponse:
                if existing.response_json and row.response_json and existing.response_json != row.response_json:
                    raise PhoneConflictError("舊帳號有重複且不同的表單回覆，請聯絡管理員核對")
                existing.response_json = existing.response_json or row.response_json
            db.delete(row)
        else:
            to_move.append(row)
    db.flush()
    for row in to_move:
        row.user_id = target.id
    db.flush()


def _merge_users(db: Session, source: User, target: User) -> None:
    """Move a transient account's data to the verified phone owner."""
    _merge_unique_user_rows(db, Membership, "organization_id", source, target)
    has_primary = db.scalars(select(Membership.id).where(
        Membership.user_id == target.id, Membership.is_primary.is_(True)
    )).first() is not None
    if has_primary:
        target.pending_class_id = None
        target.affiliation_requested_at = None
    elif target.pending_class_id is None and source.pending_class_id is not None:
        target.pending_class_id = source.pending_class_id
        target.affiliation_requested_at = source.affiliation_requested_at
    _merge_unique_user_rows(db, ActivitySignup, "activity_id", source, target)
    _merge_unique_user_rows(db, ActivityCheckin, "activity_id", source, target)
    _merge_unique_user_rows(db, RelayResponse, "relay_id", source, target)
    for model, field in (
        (Activity, "created_by"),
        (Article, "created_by"),
        (Relay, "created_by"),
        (Photo, "uploader_id"),
    ):
        db.execute(
            update(model).where(getattr(model, field) == source.id).values({field: target.id})
        )
    for field in (
        "name_en", "avatar_url", "wechat_id", "email", "bio", "profession",
        "profession_en", "company_name", "company_address", "company_founded_at",
        "position", "business_description", "referrals_needed", "personal_experience",
        "resources_offered", "chamber_chapter", "chamber_member_no", "chamber_join_date",
        "chamber_score",
    ):
        if getattr(target, field) in (None, "") and getattr(source, field) not in (None, ""):
            setattr(target, field, getattr(source, field))
    db.delete(source)
    db.flush()


def _phone_owner(db: Session, canonical: str, local: str, current: User | None) -> User | None:
    verified = db.scalars(
        select(User).where(User.verified_phone == canonical).with_for_update()
    ).first()
    if verified:
        return verified
    # Legacy contact phone is unverified. Only an unambiguous normal account can
    # be claimed automatically; duplicate numbers and admin accounts need review.
    legacy_stmt = select(User).where(User.phone.in_((local, canonical)))
    if current is not None:
        legacy_stmt = legacy_stmt.where(User.id != current.id)
    legacy = list(db.scalars(legacy_stmt.with_for_update()))
    if len(legacy) > 1:
        raise PhoneConflictError("舊資料中有多個相同手機號，請聯絡管理員核對")
    if legacy and legacy[0].verified_phone and legacy[0].verified_phone != canonical:
        raise PhoneConflictError("舊帳號已綁定其他手機號，請聯絡管理員核對")
    return legacy[0] if legacy else None


def wechat_login(db: Session, code: str, phone_code: str | None = None) -> dict:
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
    if current and current.status != Status.ACTIVE:
        raise PhoneConflictError("用戶已停用，請聯絡管理員")

    if not phone_code:
        if settings.wechat_phone_login_required and not (current and current.verified_phone):
            raise PhoneRequiredError("請授權微信手機號完成登入")
        if current:
            return _issue(current)
        user = User(
            openid=openid, unionid=unionid, name="未命名校友",
            role=Role.USER, status=Status.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _issue(user)

    canonical, local = _get_phone(phone_code)
    if current and current.verified_phone and current.verified_phone != canonical:
        raise PhoneConflictError("微信身份已綁定其他手機號，請聯絡管理員換綁")
    owner = _phone_owner(db, canonical, local, current)
    if owner and owner.status != Status.ACTIVE:
        raise PhoneConflictError("該手機號所屬帳號已停用，請聯絡管理員")
    if owner and owner.role == Role.SUPER_ADMIN and owner is not current:
        raise PhoneConflictError("管理員帳號需要人工核對後綁定")
    if current and current.role == Role.SUPER_ADMIN and owner is not None and owner is not current:
        raise PhoneConflictError("管理員帳號需要人工核對後綁定")
    target = owner or current
    if target is None:
        target = User(
            name="未命名校友", role=Role.USER, status=Status.ACTIVE,
        )
        db.add(target)
        db.flush()
    try:
        if current and current is not target:
            _merge_users(db, current, target)
        if target.openid != openid or target.verified_phone != canonical:
            target.auth_version += 1
        target.openid = openid
        target.unionid = target.unionid or unionid
        target.verified_phone = canonical
        target.phone_verified_at = datetime.now(timezone.utc)
        if not target.phone:
            target.phone = local
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise PhoneConflictError("手機號綁定衝突，請重試") from exc
    db.refresh(target)
    return _issue(target)


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
