from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.directory import (
    DirectoryTreeOut,
    MemberBrief,
    MemberDetail,
)
from app.services import directory_service

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/tree", response_model=DirectoryTreeOut)
def get_tree(current_user: CurrentUser, db: DbSession) -> DirectoryTreeOut:
    # The tree is already clipped to nodes the viewer may read.
    return directory_service.directory_tree(db, current_user)


@router.get("/members", response_model=Page[MemberBrief])
def get_members(
    current_user: CurrentUser,
    db: DbSession,
    q: str | None = Query(default=None, description="按姓名或組織路徑搜索"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[MemberBrief]:
    return directory_service.list_members(db, current_user, q, page, page_size)


@router.get("/members/{member_id}", response_model=MemberDetail)
def get_member(
    member_id: int, current_user: CurrentUser, db: DbSession
) -> MemberDetail:
    member = directory_service.get_member(db, current_user, member_id)
    if member is None:
        # Do not reveal whether the target exists outside the viewer's scope.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="無權查看或成員不存在"
        )
    return member
