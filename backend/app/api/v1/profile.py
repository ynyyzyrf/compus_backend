from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.activity import ActivityListItem
from app.schemas.profile import (
    AffiliationRequest,
    MyAffiliation,
    MyProfile,
    MyProfileUpdate,
    OrganizationOption,
)
from app.services import activity_service, affiliation_service, profile_service
from app.services.org_tree import load_org_tree

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/profile", response_model=MyProfile)
def get_my_profile(current_user: CurrentUser, db: DbSession) -> MyProfile:
    return MyProfile.model_validate(profile_service.get_my_profile(db, current_user))


@router.put("/profile", response_model=MyProfile)
def update_my_profile(
    payload: MyProfileUpdate, current_user: CurrentUser, db: DbSession
) -> MyProfile:
    user = profile_service.update_my_profile(db, current_user, payload)
    return MyProfile.model_validate(user)


@router.get("/affiliation", response_model=MyAffiliation)
def get_my_affiliation(current_user: CurrentUser, db: DbSession) -> MyAffiliation:
    return affiliation_service.my_affiliation(db, current_user)


@router.post("/affiliation", response_model=MyAffiliation)
def submit_affiliation(payload: AffiliationRequest, current_user: CurrentUser, db: DbSession) -> MyAffiliation:
    return affiliation_service.request_affiliation(db, current_user.id, payload.class_id, payload.name)


@router.get("/affiliation/options", response_model=list[OrganizationOption])
def list_affiliation_options(_: CurrentUser, db: DbSession) -> list[OrganizationOption]:
    tree = load_org_tree(db)
    return [OrganizationOption.model_validate(node) for node in tree.nodes.values()]


@router.get("/activities", response_model=list[ActivityListItem])
def list_my_activities(current_user: CurrentUser, db: DbSession) -> list[ActivityListItem]:
    rows, stats_list = activity_service.list_my_signed_activities(db, current_user)
    stats_map = {s["id"]: s for s in stats_list}
    now = datetime.now(timezone.utc)
    return [
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
            status=activity_service.compute_status(a, now),
            signup_count=stats_map.get(a.id, {}).get("signup_count", 0),
            checkin_count=stats_map.get(a.id, {}).get("checkin_count", 0),
        )
        for a in rows
    ]
