from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import DbSession, SuperAdmin
from app.schemas.photo import PhotoOut, PhotoPage
from app.services import photo_service

router = APIRouter(prefix="/admin/photos", tags=["admin/photos"])


@router.get("/pending", response_model=PhotoPage)
def list_pending_photos(
    _: SuperAdmin,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PhotoPage:
    rows, total = photo_service.list_pending_photos(
        db, page=page, page_size=page_size
    )
    return PhotoPage(
        items=[PhotoOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{photo_id}/approve", response_model=PhotoOut)
def approve_photo(photo_id: int, _: SuperAdmin, db: DbSession) -> PhotoOut:
    try:
        row = photo_service.review_photo(db, photo_id, approved=True)
    except photo_service.PhotoNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return PhotoOut.model_validate(row)


@router.post("/{photo_id}/reject", response_model=PhotoOut)
def reject_photo(photo_id: int, _: SuperAdmin, db: DbSession) -> PhotoOut:
    try:
        row = photo_service.review_photo(db, photo_id, approved=False)
    except photo_service.PhotoNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return PhotoOut.model_validate(row)
