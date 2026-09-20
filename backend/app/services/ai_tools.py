"""Read-only, controlled data tools for the admin AI assistant."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityCheckin, ActivitySignup
from app.models.content import Article
from app.models.enums import (
    ActivityStatus,
    ArticleStatus,
    PhotoStatus,
    RelayStatus,
    SignupStatus,
)
from app.models.organization import Organization
from app.models.relay import Relay, RelayResponse
from app.models.user import User
from app.models.activity import Photo


def get_activity_stats(db: Session) -> dict:
    total = db.execute(select(func.count(Activity.id))).scalar_one()
    published = db.execute(
        select(func.count(Activity.id)).where(Activity.status != ActivityStatus.DRAFT)
    ).scalar_one()
    by_status = dict(
        db.execute(select(Activity.status, func.count()).group_by(Activity.status)).all()
    )
    return {"total": total, "published": published, "by_status": by_status}


def get_signup_stats(db: Session) -> dict:
    total_signed = db.execute(
        select(func.count(ActivitySignup.id)).where(
            ActivitySignup.status == SignupStatus.SIGNED
        )
    ).scalar_one()
    by_activity = [
        {"activity_id": activity_id, "count": count}
        for activity_id, count in db.execute(
            select(ActivitySignup.activity_id, func.count())
            .where(ActivitySignup.status == SignupStatus.SIGNED)
            .group_by(ActivitySignup.activity_id)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
    ]
    return {"total_signed": total_signed, "top_activities": by_activity}


def get_checkin_stats(db: Session) -> dict:
    total_checked = db.execute(select(func.count(ActivityCheckin.id))).scalar_one()
    by_activity = [
        {"activity_id": activity_id, "count": count}
        for activity_id, count in db.execute(
            select(ActivityCheckin.activity_id, func.count())
            .group_by(ActivityCheckin.activity_id)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
    ]
    return {"total_checked_in": total_checked, "top_activities": by_activity}


def get_org_stats(db: Session) -> dict:
    total = db.execute(select(func.count(Organization.id))).scalar_one()
    by_type = dict(
        db.execute(select(Organization.type, func.count()).group_by(Organization.type)).all()
    )
    return {"total": total, "by_type": by_type}


def search_members(db: Session, keyword: str, limit: int = 10) -> list[dict]:
    keyword = keyword.strip()
    stmt = select(User).order_by(User.id.asc()).limit(limit)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = (
            select(User)
            .where(
                (User.name.ilike(pattern))
                | (User.company_name.ilike(pattern))
                | (User.profession.ilike(pattern))
                | (User.position.ilike(pattern))
            )
            .order_by(User.id.asc())
            .limit(limit)
        )
    return [
        {
            "id": user.id,
            "name": user.name,
            "company_name": user.company_name,
            "position": user.position,
            "profession": user.profession,
        }
        for user in db.execute(stmt).scalars().all()
    ]


def get_relay_stats(db: Session) -> dict:
    total = db.execute(select(func.count(Relay.id))).scalar_one()
    open_count = db.execute(
        select(func.count(Relay.id)).where(Relay.status == RelayStatus.OPEN)
    ).scalar_one()
    total_responses = db.execute(select(func.count(RelayResponse.id))).scalar_one()
    return {"total": total, "open": open_count, "total_responses": total_responses}


def get_content_stats(db: Session) -> dict:
    total = db.execute(select(func.count(Article.id))).scalar_one()
    published = db.execute(
        select(func.count(Article.id)).where(Article.status == ArticleStatus.PUBLISHED)
    ).scalar_one()
    by_type = dict(
        db.execute(select(Article.type, func.count()).group_by(Article.type)).all()
    )
    photos = dict(
        db.execute(select(Photo.status, func.count()).group_by(Photo.status)).all()
    )
    return {
        "total": total,
        "published": published,
        "by_type": by_type,
        "photos": {
            "pending": photos.get(PhotoStatus.PENDING, 0),
            "approved": photos.get(PhotoStatus.APPROVED, 0),
            "rejected": photos.get(PhotoStatus.REJECTED, 0),
        },
    }


def generate_activity_summary(db: Session) -> dict:
    activity = db.execute(
        select(Activity)
        .where(Activity.status != ActivityStatus.DRAFT)
        .order_by(Activity.start_at.desc(), Activity.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if activity is None:
        return {"title": "", "summary": "暫無已發布活動。"}

    signups = db.execute(
        select(func.count(ActivitySignup.id)).where(
            ActivitySignup.activity_id == activity.id,
            ActivitySignup.status == SignupStatus.SIGNED,
        )
    ).scalar_one()
    checkins = db.execute(
        select(func.count(ActivityCheckin.id)).where(
            ActivityCheckin.activity_id == activity.id
        )
    ).scalar_one()
    return {
        "activity_id": activity.id,
        "title": activity.title,
        "location": activity.location,
        "start_at": activity.start_at.isoformat(),
        "signup_count": signups,
        "checkin_count": checkins,
        "summary": (
            f"{activity.title} 將在 {activity.location} 舉辦，"
            f"目前 {signups} 人報名，{checkins} 人已簽到。"
        ),
    }


def build_tool_context(db: Session, message: str) -> dict:
    return {
        "question": message,
        "tools": {
            "activity_stats": get_activity_stats(db),
            "signup_stats": get_signup_stats(db),
            "checkin_stats": get_checkin_stats(db),
            "org_stats": get_org_stats(db),
            "member_search": search_members(db, message),
            "relay_stats": get_relay_stats(db),
            "content_stats": get_content_stats(db),
            "activity_summary": generate_activity_summary(db),
        },
    }
