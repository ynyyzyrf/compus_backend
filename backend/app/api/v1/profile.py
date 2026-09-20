from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.profile import MyProfile, MyProfileUpdate
from app.services import profile_service

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
