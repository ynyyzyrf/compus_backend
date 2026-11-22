from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import case, func, or_, select, update

from app.core.deps import CurrentUser, DbSession
from app.models.connection import AlumniConnection
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


def _participant(user_id: int):
    return or_(AlumniConnection.user_low_id == user_id, AlumniConnection.user_high_id == user_id)


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
    return {"eligible": eligible, "discoverable": eligible and user.alumni_discoverable, "unread": unread}


@router.put("/preferences", response_model=Preferences)
def update_preferences(payload: Preferences, user: CurrentUser, db: DbSession):
    if payload.discoverable and directory_service.alumni_school(db, load_org_tree(db), user.id) is None:
        raise HTTPException(403, "归属审核通过后才可开启校友查找")
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
    return [
        ConnectionItem(
            peer_id=peer.id, name=peer.name,
            org_path=tree.path_name(class_id) if class_id in tree.nodes else "",
            status=record.status, incoming=record.sender_id != user.id,
            message=record.message,
            unread=record.sender_id != user.id and record.status == "pending" and record.read_at is None,
            shares_wechat=record.status == "accepted" and (
                record.low_shares_wechat if user.id == record.user_low_id else record.high_shares_wechat
            ),
            peer_wechat_id=peer.wechat_id if record.status == "accepted" and (
                record.low_shares_wechat if peer.id == record.user_low_id else record.high_shares_wechat
            ) else None,
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
    if row and row.responded_at and row.responded_at > now - timedelta(days=7):
        raise HTTPException(429, "申请暂不可重发，请稍后再试")
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
    if user.id == row.user_low_id:
        row.low_shares_wechat = payload.share
    else:
        row.high_shares_wechat = payload.share
    db.commit()
    return payload
