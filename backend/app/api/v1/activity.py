from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.activity import (
    ActivityDetail,
    ActivityListItem,
    CheckinRequest,
    CheckinResult,
    SignupRequest,
    SignupResult,
)
from app.services import activity_service
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

router = APIRouter(prefix="/activities", tags=["activities"])


def _serialize(activity, stats: dict, *, my_signed_up=False, my_checked_in=False):
    status_value = activity_service.compute_status(activity)
    return {
        "id": activity.id,
        "title": activity.title,
        "cover_url": activity.cover_url,
        "description": activity.description,
        "location": activity.location,
        "organizer": activity.organizer,
        "start_at": activity.start_at,
        "end_at": activity.end_at,
        "signup_start_at": activity.signup_start_at,
        "signup_end_at": activity.signup_end_at,
        "capacity": activity.capacity,
        "status": status_value,
        "signup_count": stats.get("signup_count", 0),
        "checkin_count": stats.get("checkin_count", 0),
        "created_by": activity.created_by,
        "my_signed_up": my_signed_up,
        "my_checked_in": my_checked_in,
    }


@router.get("", response_model=list[ActivityListItem])
def list_activities(
    _: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(signing|upcoming|ongoing|finished)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[ActivityListItem]:
    rows, stats_list = activity_service.list_activities(
        db, status_filter=status_filter, page=page, page_size=page_size
    )
    stats_map = {s["id"]: s for s in stats_list}
    items = []
    now = datetime.now(timezone.utc)
    for a in rows:
        status_value = activity_service.compute_status(a, now)
        if status_filter and status_value != status_filter:
            continue
        s = stats_map.get(a.id, {})
        items.append(
            ActivityListItem(
                id=a.id,
                title=a.title,
                cover_url=a.cover_url,
                description=a.description,
                location=a.location,
                organizer=a.organizer,
                start_at=a.start_at,
                end_at=a.end_at,
                signup_start_at=a.signup_start_at,
                signup_end_at=a.signup_end_at,
                capacity=a.capacity,
                status=status_value,
                signup_count=s.get("signup_count", 0),
                checkin_count=s.get("checkin_count", 0),
            )
        )
    return items


@router.get("/{activity_id}", response_model=ActivityDetail)
def get_activity(
    activity_id: int, current_user: CurrentUser, db: DbSession
) -> ActivityDetail:
    activity, my_signed_up, my_checked_in = activity_service.get_activity_for_user(
        db, activity_id, current_user
    )
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="活動不存在"
        )
    stats = activity_service._stats_for(db, [activity_id])[0]
    payload = _serialize(
        activity,
        stats,
        my_signed_up=my_signed_up,
        my_checked_in=my_checked_in,
    )
    return ActivityDetail(**payload)


@router.post("/{activity_id}/signup", response_model=SignupResult, status_code=status.HTTP_201_CREATED)
def signup_activity(
    activity_id: int, payload: SignupRequest, current_user: CurrentUser, db: DbSession
) -> SignupResult:
    try:
        row = activity_service.signup(
            db, activity_id, current_user, payload.phone, payload.remark
        )
    except activity_service.AlreadySignedUp as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except activity_service.NotInSignupWindow as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except activity_service.CapacityReached as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except activity_service.SignupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return SignupResult.model_validate(row)


@router.delete("/{activity_id}/signup", status_code=status.HTTP_204_NO_CONTENT)
def cancel_signup(
    activity_id: int, current_user: CurrentUser, db: DbSession
) -> None:
    try:
        ok = activity_service.cancel_signup(db, activity_id, current_user)
    except activity_service.CancelTooLate as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到報名記錄")


@router.post("/{activity_id}/checkin", response_model=CheckinResult)
def checkin_activity(
    activity_id: int, payload: CheckinRequest, current_user: CurrentUser, db: DbSession
) -> CheckinResult:
    try:
        row = activity_service.checkin(db, activity_id, current_user, payload.token)
    except activity_service.InvalidToken as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except activity_service.NotSignedUp as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except activity_service.AlreadyCheckedIn as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except activity_service.NotInCheckinWindow as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except activity_service.CheckinError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return CheckinResult.model_validate(row)
