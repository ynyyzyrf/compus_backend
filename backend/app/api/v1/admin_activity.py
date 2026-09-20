from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import DbSession, SuperAdmin
from app.schemas.activity import (
    ActivityAdminOut,
    ActivityAdminPage,
    ActivityCreate,
    ActivityUpdate,
    CheckinCodeOut,
    SignupList,
)
from app.services import activity_service
from app.services.qr_token import issue_checkin_token

router = APIRouter(prefix="/admin/activities", tags=["admin/activities"])


def _admin_view(activity, stats: dict) -> ActivityAdminOut:
    return ActivityAdminOut(
        id=activity.id,
        title=activity.title,
        cover_url=activity.cover_url,
        description=activity.description,
        location=activity.location,
        organizer=activity.organizer,
        start_at=activity.start_at,
        end_at=activity.end_at,
        signup_start_at=activity.signup_start_at,
        signup_end_at=activity.signup_end_at,
        capacity=activity.capacity,
        status=activity_service.compute_status(activity),
        signup_count=stats.get("signup_count", 0),
        checkin_count=stats.get("checkin_count", 0),
        created_by=activity.created_by,
    )


@router.get("", response_model=ActivityAdminPage)
def list_activities(
    _: SuperAdmin,
    db: DbSession,
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(draft|signing|upcoming|ongoing|finished)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ActivityAdminPage:
    rows, total = activity_service.list_admin_activities(
        db, page=page, page_size=page_size, status=status_filter
    )
    stats_map = {s["id"]: s for s in activity_service._stats_for(db, [a.id for a in rows])}
    items = [_admin_view(a, stats_map.get(a.id, {})) for a in rows]
    return ActivityAdminPage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ActivityAdminOut, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreate, admin: SuperAdmin, db: DbSession) -> ActivityAdminOut:
    a = activity_service.create_activity(db, payload, admin)
    return _admin_view(a, {"signup_count": 0, "checkin_count": 0})


@router.put("/{activity_id}", response_model=ActivityAdminOut)
def update_activity(
    activity_id: int, payload: ActivityUpdate, _: SuperAdmin, db: DbSession
) -> ActivityAdminOut:
    a = activity_service.update_activity(db, activity_id, payload)
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活動不存在")
    stats = activity_service._stats_for(db, [a.id])[0]
    return _admin_view(a, stats)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: int, _: SuperAdmin, db: DbSession) -> None:
    if not activity_service.delete_activity(db, activity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活動不存在")


@router.post("/{activity_id}/checkin-code", response_model=CheckinCodeOut)
def issue_checkin_code(
    activity_id: int, _: SuperAdmin, db: DbSession
) -> CheckinCodeOut:
    a = db.get(activity_service.Activity, activity_id)  # type: ignore[attr-defined]
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活動不存在")
    token, expires_at = issue_checkin_token(activity_id)
    return CheckinCodeOut(activity_id=activity_id, token=token, expires_at=expires_at)


@router.get("/{activity_id}/signups", response_model=SignupList)
def list_signups(activity_id: int, _: SuperAdmin, db: DbSession) -> SignupList:
    a = db.get(activity_service.Activity, activity_id)  # type: ignore[attr-defined]
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活動不存在")
    roster = activity_service.admin_roster(db, activity_id)
    return SignupList(**roster)
