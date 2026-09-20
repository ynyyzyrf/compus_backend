"""Activity photo submission and review workflow."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity, Photo
from app.models.enums import ActivityStatus, PhotoStatus, Role
from app.models.user import User
from app.services.photo_storage import StorageDriver, get_storage_driver


class PhotoError(Exception):
    pass


class ActivityNotFound(PhotoError):
    pass


class PhotoNotFound(PhotoError):
    pass


def _visible_activity(db: Session, activity_id: int) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status == ActivityStatus.DRAFT:
        raise ActivityNotFound("活動不存在")
    return activity


def list_activity_photos(db: Session, activity_id: int) -> list[Photo]:
    _visible_activity(db, activity_id)
    return list(
        db.execute(
            select(Photo)
            .where(
                Photo.activity_id == activity_id,
                Photo.status == PhotoStatus.APPROVED,
            )
            .order_by(Photo.created_at.desc(), Photo.id.desc())
        )
        .scalars()
        .all()
    )


def submit_activity_photo(
    db: Session,
    activity_id: int,
    user: User,
    file_url: str,
    storage: StorageDriver | None = None,
) -> Photo:
    _visible_activity(db, activity_id)
    stored = (storage or get_storage_driver()).normalize_image_url(file_url)
    now = datetime.now(timezone.utc)
    is_admin = user.role == Role.SUPER_ADMIN
    row = Photo(
        activity_id=activity_id,
        uploader_id=user.id,
        file_url=stored.file_url,
        status=PhotoStatus.APPROVED if is_admin else PhotoStatus.PENDING,
        reviewed_at=now if is_admin else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_pending_photos(
    db: Session, page: int = 1, page_size: int = 20
) -> tuple[list[Photo], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    stmt = select(Photo).where(Photo.status == PhotoStatus.PENDING)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Photo.created_at.asc(), Photo.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), total


def list_user_photos(
    db: Session, user: User, page: int = 1, page_size: int = 20
) -> tuple[list[Photo], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    stmt = select(Photo).where(Photo.uploader_id == user.id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Photo.created_at.desc(), Photo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), total


def review_photo(db: Session, photo_id: int, approved: bool) -> Photo:
    row = db.get(Photo, photo_id)
    if row is None:
        raise PhotoNotFound("照片不存在")
    row.status = PhotoStatus.APPROVED if approved else PhotoStatus.REJECTED
    row.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
