"""Activity + signup + checkin lifecycle (PRD §10-§12, §22.3)."""

from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import (
    Activity,
    ActivityCheckin,
    ActivitySignup,
)
from app.models.enums import (
    ActivityStatus,
    CheckinMethod,
    Role,
    SignupStatus,
)
from app.models.organization import Membership, Organization
from app.models.user import User
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

# ---- status computation ----


def compute_status(activity: Activity, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if activity.status == ActivityStatus.DRAFT:
        return ActivityStatus.DRAFT
    if now < activity.signup_end_at:
        return ActivityStatus.SIGNING
    if now < activity.start_at:
        return ActivityStatus.UPCOMING
    if now <= activity.end_at:
        return ActivityStatus.ONGOING
    return ActivityStatus.FINISHED


# ---- read: user-facing ----


def list_activities(
    db: Session,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Activity], list[dict]]:
    """Return (activities, per-row stats). Caller filters by computed status."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.execute(
        select(func.count(Activity.id)).where(Activity.status != ActivityStatus.DRAFT)
    ).scalar_one()
    rows = db.execute(
        select(Activity)
        .where(Activity.status != ActivityStatus.DRAFT)
        .order_by(Activity.start_at.desc(), Activity.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    if not rows:
        return [], []
    stats = _stats_for(db, [a.id for a in rows])
    return list(rows), stats


def list_my_signed_activities(db: Session, user: User) -> tuple[list[Activity], list[dict]]:
    rows = db.execute(
        select(Activity)
        .join(ActivitySignup, ActivitySignup.activity_id == Activity.id)
        .where(
            Activity.status != ActivityStatus.DRAFT,
            ActivitySignup.user_id == user.id,
            ActivitySignup.status == SignupStatus.SIGNED,
        )
        .order_by(Activity.start_at.desc(), Activity.id.desc())
    ).scalars().all()
    if not rows:
        return [], []
    stats = _stats_for(db, [a.id for a in rows])
    return list(rows), stats


def _stats_for(db: Session, activity_ids: Iterable[int]) -> list[dict]:
    ids = list(activity_ids)
    if not ids:
        return []
    signup_counts = dict(
        db.execute(
            select(ActivitySignup.activity_id, func.count())
            .where(
                ActivitySignup.activity_id.in_(ids),
                ActivitySignup.status == SignupStatus.SIGNED,
            )
            .group_by(ActivitySignup.activity_id)
        ).all()
    )
    checkin_counts = dict(
        db.execute(
            select(ActivityCheckin.activity_id, func.count())
            .where(ActivityCheckin.activity_id.in_(ids))
            .group_by(ActivityCheckin.activity_id)
        ).all()
    )
    return [
        {
            "id": aid,
            "signup_count": signup_counts.get(aid, 0),
            "checkin_count": checkin_counts.get(aid, 0),
        }
        for aid in ids
    ]


def get_activity_for_user(
    db: Session, activity_id: int, user: User
) -> tuple[Activity | None, bool, bool]:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status == ActivityStatus.DRAFT:
        if activity is None or (activity.status == ActivityStatus.DRAFT and user.role != Role.SUPER_ADMIN):
            return None, False, False
    signup = db.execute(
        select(ActivitySignup).where(
            ActivitySignup.activity_id == activity_id,
            ActivitySignup.user_id == user.id,
        )
    ).scalar_one_or_none()
    my_signed_up = signup is not None and signup.status == SignupStatus.SIGNED
    checked = db.execute(
        select(ActivityCheckin.id).where(
            ActivityCheckin.activity_id == activity_id,
            ActivityCheckin.user_id == user.id,
        )
    ).first()
    return activity, my_signed_up, checked is not None


# ---- signup ----


class SignupError(Exception):
    code = "signup_failed"


class NotInSignupWindow(SignupError):
    code = "not_in_window"


class CapacityReached(SignupError):
    code = "capacity_reached"


class AlreadySignedUp(SignupError):
    code = "already_signed_up"


def signup(
    db: Session, activity_id: int, user: User, phone: str | None, remark: str | None
) -> ActivitySignup:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status == ActivityStatus.DRAFT:
        raise SignupError("活動不存在或尚未發布")

    now = datetime.now(timezone.utc)
    if not (activity.signup_start_at <= now <= activity.signup_end_at):
        raise NotInSignupWindow("不在報名時間段內")

    # capacity check
    if activity.capacity is not None:
        count = db.execute(
            select(func.count(ActivitySignup.id)).where(
                ActivitySignup.activity_id == activity_id,
                ActivitySignup.status == SignupStatus.SIGNED,
            )
        ).scalar_one()
        if count >= activity.capacity:
            raise CapacityReached("報名人數已滿")

    existing = db.execute(
        select(ActivitySignup).where(
            ActivitySignup.activity_id == activity_id,
            ActivitySignup.user_id == user.id,
        )
    ).scalar_one_or_none()
    if existing and existing.status == SignupStatus.SIGNED:
        raise AlreadySignedUp("已報名，無需重複")
    if existing and existing.status == SignupStatus.CANCELLED:
        # re-sign after cancellation
        existing.status = SignupStatus.SIGNED
        existing.phone = phone
        existing.remark = remark
        db.commit()
        db.refresh(existing)
        return existing

    signup_row = ActivitySignup(
        activity_id=activity_id,
        user_id=user.id,
        phone=phone,
        remark=remark,
        status=SignupStatus.SIGNED,
    )
    db.add(signup_row)
    db.commit()
    db.refresh(signup_row)
    return signup_row


class CancelTooLate(SignupError):
    code = "too_late"


def cancel_signup(db: Session, activity_id: int, user: User) -> bool:
    now = datetime.now(timezone.utc)
    activity = db.get(Activity, activity_id)
    if activity is None:
        return False
    if now > activity.signup_end_at:
        raise CancelTooLate("已過報名截止時間，無法取消")
    signup_row = db.execute(
        select(ActivitySignup).where(
            ActivitySignup.activity_id == activity_id,
            ActivitySignup.user_id == user.id,
        )
    ).scalar_one_or_none()
    if signup_row is None or signup_row.status != SignupStatus.SIGNED:
        return False
    signup_row.status = SignupStatus.CANCELLED
    db.commit()
    return True


# ---- checkin ----


class CheckinError(Exception):
    code = "checkin_failed"


class InvalidToken(CheckinError):
    code = "invalid_token"


class AlreadyCheckedIn(CheckinError):
    code = "already_checked_in"


class NotSignedUp(CheckinError):
    code = "not_signed_up"


class NotInCheckinWindow(CheckinError):
    code = "not_in_window"


def checkin(db: Session, activity_id: int, user: User, token: str) -> ActivityCheckin:
    from app.services.qr_token import decode_checkin_token

    if not decode_checkin_token(token, activity_id):
        raise InvalidToken("簽到碼無效或已過期")

    activity = db.get(Activity, activity_id)
    if activity is None or activity.status == ActivityStatus.DRAFT:
        raise CheckinError("活動不存在")

    # window: [start_at - 1h, end_at]
    now = datetime.now(timezone.utc)
    earliest = activity.start_at.replace(tzinfo=timezone.utc) - __import__("datetime").timedelta(hours=1)
    if now < earliest or now > activity.end_at:
        raise NotInCheckinWindow("不在簽到時間段內")

    signup_row = db.execute(
        select(ActivitySignup).where(
            ActivitySignup.activity_id == activity_id,
            ActivitySignup.user_id == user.id,
            ActivitySignup.status == SignupStatus.SIGNED,
        )
    ).scalar_one_or_none()
    if signup_row is None:
        raise NotSignedUp("未報名，不能簽到")

    exists = db.execute(
        select(ActivityCheckin.id).where(
            ActivityCheckin.activity_id == activity_id,
            ActivityCheckin.user_id == user.id,
        )
    ).first()
    if exists is not None:
        raise AlreadyCheckedIn("已簽到，無需重複")

    row = ActivityCheckin(
        activity_id=activity_id,
        user_id=user.id,
        signup_id=signup_row.id,
        checkin_at=now,
        checkin_method=CheckinMethod.QRCODE,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---- admin: roster + checkin stats ----


def admin_roster(db: Session, activity_id: int) -> dict:
    activity = db.get(Activity, activity_id)
    if activity is None:
        return {
            "items": [], "total": 0, "signup_count": 0, "checkin_count": 0,
            "checkin_rate": 0.0, "by_college": {},
        }

    rows = db.execute(
        select(ActivitySignup, User)
        .join(User, User.id == ActivitySignup.user_id)
        .where(ActivitySignup.activity_id == activity_id)
        .order_by(ActivitySignup.created_at)
    ).all()

    tree = load_org_tree(db)
    checkin_map = dict(
        db.execute(
            select(ActivityCheckin.user_id, ActivityCheckin.checkin_at).where(
                ActivityCheckin.activity_id == activity_id
            )
        ).all()
    )

    items = []
    college_counter: Counter[str] = Counter()
    checkin_count = 0
    signup_count = 0
    for signup_row, user in rows:
        if signup_row.status != SignupStatus.SIGNED:
            continue
        signup_count += 1
        class_id = get_primary_class_id(db, user.id)
        org_path = tree.path_name(class_id) if class_id else ""
        college = ""
        if class_id and class_id in tree.nodes:
            cur = tree.nodes[class_id]
            while cur and cur.type != "college":
                cur = tree.nodes.get(cur.parent_id) if cur.parent_id else None
            if cur:
                college = cur.name
                college_counter[college] += 1
        checked_at = checkin_map.get(user.id)
        if checked_at is not None:
            checkin_count += 1
        items.append({
            "id": signup_row.id,
            "user_id": user.id,
            "user_name": user.name,
            "user_org_path": org_path,
            "phone": signup_row.phone,
            "remark": signup_row.remark,
            "status": signup_row.status,
            "created_at": signup_row.created_at,
            "checked_in": checked_at is not None,
            "checkin_at": checked_at,
        })

    rate = (checkin_count / signup_count) if signup_count else 0.0
    return {
        "items": items,
        "total": signup_count,
        "signup_count": signup_count,
        "checkin_count": checkin_count,
        "checkin_rate": rate,
        "by_college": dict(college_counter),
    }


# ---- admin CRUD ----


def create_activity(db: Session, payload, creator: User) -> Activity:
    a = Activity(
        title=payload.title,
        cover_url=payload.cover_url,
        description=payload.description,
        location=payload.location,
        organizer=payload.organizer,
        start_at=payload.start_at,
        end_at=payload.end_at,
        signup_start_at=payload.signup_start_at,
        signup_end_at=payload.signup_end_at,
        capacity=payload.capacity,
        status=payload.status,
        created_by=creator.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def update_activity(db: Session, activity_id: int, payload) -> Activity | None:
    a = db.get(Activity, activity_id)
    if a is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(a, key, value)
    db.commit()
    db.refresh(a)
    return a


def delete_activity(db: Session, activity_id: int) -> bool:
    a = db.get(Activity, activity_id)
    if a is None:
        return False
    db.delete(a)
    db.commit()
    return True


def list_admin_activities(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[Activity], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    stmt = select(Activity)
    if status:
        stmt = stmt.where(Activity.status == status)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = db.execute(
        stmt.order_by(Activity.start_at.desc(), Activity.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), total
