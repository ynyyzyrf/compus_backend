from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.photo import PhotoCreate, PhotoOut, PhotoPage
from app.services import photo_service
from app.services.photo_storage import StorageError

router = APIRouter(prefix="/activities", tags=["photos"])

me_router = APIRouter(prefix="/me/photos", tags=["photos"])


@me_router.get("", response_model=PhotoPage)
def list_my_photos(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PhotoPage:
    rows, total = photo_service.list_user_photos(
        db, current_user, page=page, page_size=page_size
    )
    return PhotoPage(
        items=[PhotoOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{activity_id}/photos", response_model=list[PhotoOut])
def list_activity_photos(
    activity_id: int, _: CurrentUser, db: DbSession
) -> list[PhotoOut]:
    try:
        rows = photo_service.list_activity_photos(db, activity_id)
    except photo_service.ActivityNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [PhotoOut.model_validate(row) for row in rows]


@router.post(
    "/{activity_id}/photos",
    response_model=PhotoOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_activity_photo(
    activity_id: int, payload: PhotoCreate, current_user: CurrentUser, db: DbSession
) -> PhotoOut:
    try:
        row = photo_service.submit_activity_photo(
            db, activity_id, current_user, payload.file_url
        )
    except photo_service.ActivityNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return PhotoOut.model_validate(row)
