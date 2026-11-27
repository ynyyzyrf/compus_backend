from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import case, func, or_, select, update

from app.core.deps import CurrentUser, DbSession
from app.models.connection import AlumniConnection, AlumniMessage
from app.models.enums import Status
from app.models.organization import Membership
from app.models.user import User
from app.services import directory_service, wechat_moderation
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

router = APIRouter(prefix="/connections", tags=["connections"])


class Preferences(BaseModel):
    discoverable: bool


class RequestMessage(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""


class Decision(BaseModel):
    action: Literal["accept", "decline"]


class WechatSharing(BaseModel):
    share: bool


class ReadRequests(BaseModel):
    peer_ids: list[int] = Field(max_length=100)


class FriendMessageInput(BaseModel):
    client_id: Annotated[str, StringConstraints(min_length=8, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class FriendMessageRead(BaseModel):
    through_id: int = Field(gt=0)


class FriendMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    message: str
    created_at: datetime


class FriendMessagePage(BaseModel):
    peer_name: str
    items: list[FriendMessageOut]
    has_more: bool


class ConnectionItem(BaseModel):
    peer_id: int
    name: str
    org_path: str
    status: Literal["pending", "accepted", "declined"]
    incoming: bool
    message: str
    unread: bool
    shares_wechat: bool = False
    peer_wechat_id: str | None = None
    unread_messages: int = 0


def _participant(user_id: int):
    return or_(AlumniConnection.user_low_id == user_id, AlumniConnection.user_high_id == user_id)


def _unread_messages(db: DbSession, viewer_id: int) -> dict[int, int]:
    return dict(db.execute(
        select(AlumniMessage.sender_id, func.count())
        .join(AlumniConnection, (AlumniMessage.user_low_id == AlumniConnection.user_low_id) & (AlumniMessage.user_high_id == AlumniConnection.user_high_id))
        .join(User, User.id == AlumniMessage.sender_id)
        .where(_participant(viewer_id), AlumniConnection.status == "accepted", User.status == Status.ACTIVE,
               AlumniMessage.sender_id != viewer_id, AlumniMessage.read_at.is_(None))
        .group_by(AlumniMessage.sender_id)
    ).all())


@router.get("/summary")
def get_summary(user: CurrentUser, db: DbSession):
    tree = load_org_tree(db)
    eligible = directory_service.alumni_school(db, tree, user.id) is not None
    unread = db.scalar(
        select(func.count()).select_from(AlumniConnection).join(User, User.id == AlumniConnection.sender_id)
        .where(
            _participant(user.id), AlumniConnection.sender_id != user.id, User.status == Status.ACTIVE,
            AlumniConnection.status == "pending", AlumniConnection.read_at.is_(None),
        )
    )
    return {"eligible": eligible, "discoverable": eligible and user.alumni_discoverable and user.basic_visibility != "private", "unread": unread,
            "unread_messages": sum(_unread_messages(db, user.id).values())}


@router.put("/preferences", response_model=Preferences)
def update_preferences(payload: Preferences, user: CurrentUser, db: DbSession):
    if payload.discoverable and directory_service.alumni_school(db, load_org_tree(db), user.id) is None:
        raise HTTPException(403, "归属审核通过后才可开启校友查找")
    if payload.discoverable and user.basic_visibility == "private":
        raise HTTPException(409, "请先在个人名片中修改基础资料的可见范围")
    user.alumni_discoverable = payload.discoverable
    db.commit()
    return payload


@router.get("", response_model=list[ConnectionItem])
def list_connections(user: CurrentUser, db: DbSession):
    peer_id = case(
        (AlumniConnection.user_low_id == user.id, AlumniConnection.user_high_id),
        else_=AlumniConnection.user_low_id,
    )
    rows = db.execute(
        select(AlumniConnection, User, Membership.organization_id)
        .join(User, User.id == peer_id)
        .outerjoin(Membership, (Membership.user_id == User.id) & Membership.is_primary.is_(True))
        .where(_participant(user.id), User.status == Status.ACTIVE)
        .order_by(AlumniConnection.requested_at.desc())
    ).all()
    tree = load_org_tree(db)
    unread_messages = _unread_messages(db, user.id)
    return [
        ConnectionItem(
            peer_id=peer.id, name=peer.name,
            org_path=tree.path_name(class_id) if class_id in tree.nodes else "",
            status=record.status, incoming=record.sender_id != user.id,
            message=record.message,
            unread=record.sender_id != user.id and record.status == "pending" and record.read_at is None,
            shares_wechat=record.status == "accepted" and user.contact_visibility != "private" and (
                record.low_shares_wechat if user.id == record.user_low_id else record.high_shares_wechat
            ),
            peer_wechat_id=peer.wechat_id if record.status == "accepted" and peer.contact_visibility != "private" and (
                record.low_shares_wechat if peer.id == record.user_low_id else record.high_shares_wechat
            ) else None,
            unread_messages=unread_messages.get(peer.id, 0),
        )
        for record, peer, class_id in rows
    ]


@router.post("/read", status_code=204)
def mark_read(payload: ReadRequests, user: CurrentUser, db: DbSession):
    peers = set(payload.peer_ids)
    db.execute(update(AlumniConnection).where(
        _participant(user.id), AlumniConnection.sender_id.in_(peers),
        AlumniConnection.sender_id != user.id, AlumniConnection.read_at.is_(None),
    ).values(read_at=datetime.now(UTC)))
    db.commit()


@router.post("/{peer_id}/request", status_code=201)
def send_request(peer_id: int, payload: RequestMessage, user: CurrentUser, db: DbSession):
    if peer_id == user.id:
        raise HTTPException(400, "不能向自己发送好友申请")
    # Lock the two users in a stable order to serialize pair changes and rate limits.
    ids = sorted((user.id, peer_id))
    users = {row.id: row for row in db.scalars(
        select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update()
        .execution_options(populate_existing=True)
    )}
    if user.id not in users or users[user.id].status != Status.ACTIVE:
        raise HTTPException(403, "账号不可用")
    peer = users.get(peer_id)
    target_class_id = get_primary_class_id(db, peer_id) if peer is not None else None
    if target_class_id is None or not directory_service.can_find_alumnus(
        db, load_org_tree(db), users[user.id], peer, target_class_id
    ):
        raise HTTPException(404, "该校友目前无法接收申请")
    now = datetime.now(UTC)
    row = db.get(AlumniConnection, tuple(ids), with_for_update=True)
    if row and row.status != "declined":
        if row.status == "pending" and row.sender_id == user.id:
            return {"status": row.status}
        raise HTTPException(409, "已有好友关系或待处理申请")
    daily_count = db.scalar(select(func.count()).select_from(AlumniConnection).where(
        AlumniConnection.sender_id == user.id, AlumniConnection.requested_at > now - timedelta(days=1)
    ))
    if daily_count >= 10:
        raise HTTPException(429, "今天发送的好友申请已达上限")
    wechat_moderation.check_alumni_message(user.openid, payload.message)
    if row is None:
        row = AlumniConnection(user_low_id=ids[0], user_high_id=ids[1])
        db.add(row)
    row.sender_id = user.id
    row.status = "pending"
    row.message = payload.message
    row.requested_at = now
    row.read_at = row.responded_at = None
    db.commit()
    return {"status": "pending"}


@router.post("/{peer_id}/respond")
def respond(peer_id: int, payload: Decision, user: CurrentUser, db: DbSession):
    row = db.get(AlumniConnection, tuple(sorted((peer_id, user.id))), with_for_update=True)
    if row is None or row.sender_id == user.id:
        raise HTTPException(404, "好友申请不存在")
    status = "accepted" if payload.action == "accept" else "declined"
    if row.status == status:
        return {"status": status}
    if row.status != "pending":
        raise HTTPException(409, "好友申请已处理")
    if status == "accepted":
        sender = db.get(User, peer_id)
        tree = load_org_tree(db)
        if sender is None or sender.status != Status.ACTIVE or any(
            directory_service.alumni_school(db, tree, uid) is None for uid in (user.id, peer_id)
        ):
            raise HTTPException(409, "校友归属已变更，暂时无法通过申请")
    row.status = status
    row.responded_at = datetime.now(UTC)
    row.read_at = row.read_at or row.responded_at
    db.commit()
    return {"status": status}


@router.put("/{peer_id}/wechat", response_model=WechatSharing)
def share_wechat(peer_id: int, payload: WechatSharing, user: CurrentUser, db: DbSession):
    row = db.get(AlumniConnection, tuple(sorted((peer_id, user.id))), with_for_update=True)
    if row is None or row.status != "accepted":
        raise HTTPException(404, "好友关系不存在")
    if payload.share and not user.wechat_id:
        raise HTTPException(400, "请先在个人名片中填写微信号")
    if payload.share and user.contact_visibility == "private":
        raise HTTPException(409, "请先在个人名片中允许好友查看联系方式")
    if user.id == row.user_low_id:
        row.low_shares_wechat = payload.share
    else:
        row.high_shares_wechat = payload.share
    db.commit()
    return payload


def _require_friend(db: DbSession, user_id: int, peer_id: int, *, lock: bool = False) -> User:
    peer = db.get(User, peer_id)
    pair = tuple(sorted((user_id, peer_id)))
    connection = db.get(AlumniConnection, pair, with_for_update=lock)
    if connection is None or connection.status != "accepted" or peer is None or peer.status != Status.ACTIVE:
        raise HTTPException(404, "好友关系不存在")
    return peer


def _message_pair(user_id: int, peer_id: int):
    low, high = sorted((user_id, peer_id))
    return AlumniMessage.user_low_id == low, AlumniMessage.user_high_id == high


@router.get("/{peer_id}/messages", response_model=FriendMessagePage)
def list_messages(
    peer_id: int, user: CurrentUser, db: DbSession,
    before_id: int | None = Query(default=None, gt=0),
    page_size: int = Query(default=30, ge=1, le=60),
):
    peer = _require_friend(db, user.id, peer_id)
    stmt = select(AlumniMessage).where(*_message_pair(user.id, peer_id))
    if before_id is not None:
        stmt = stmt.where(AlumniMessage.id < before_id)
    messages = list(db.scalars(stmt.order_by(AlumniMessage.id.desc()).limit(page_size + 1)))
    return FriendMessagePage(
        peer_name=peer.name,
        items=[FriendMessageOut.model_validate(message) for message in reversed(messages[:page_size])],
        has_more=len(messages) > page_size,
    )


@router.post("/{peer_id}/messages", status_code=201, response_model=FriendMessageOut)
def send_message(peer_id: int, payload: FriendMessageInput, user: CurrentUser, db: DbSession):
    _require_friend(db, user.id, peer_id, lock=True)
    previous = db.scalar(select(AlumniMessage).where(
        *_message_pair(user.id, peer_id), AlumniMessage.sender_id == user.id, AlumniMessage.client_id == payload.client_id,
    ))
    if previous is not None:
        if previous.message != payload.message:
            raise HTTPException(409, "留言内容已变更，请重新发送")
        return previous
    wechat_moderation.check_alumni_message(user.openid, payload.message)
    low, high = sorted((user.id, peer_id))
    message = AlumniMessage(user_low_id=low, user_high_id=high, sender_id=user.id, **payload.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.post("/{peer_id}/messages/read", status_code=204)
def mark_messages_read(peer_id: int, payload: FriendMessageRead, user: CurrentUser, db: DbSession):
    _require_friend(db, user.id, peer_id)
    db.execute(update(AlumniMessage).where(
        *_message_pair(user.id, peer_id), AlumniMessage.sender_id == peer_id,
        AlumniMessage.read_at.is_(None), AlumniMessage.id <= payload.through_id,
    ).values(read_at=datetime.now(UTC)))
    db.commit()
