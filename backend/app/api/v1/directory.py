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
    q: str | None = Query(default=None, max_length=80, description="按姓名或组织路径搜索"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    discover: bool = False,
    entry_year: int | None = Query(default=None, ge=1900, le=2100),
    college_id: int | None = Query(default=None, ge=1),
    department_id: int | None = Query(default=None, ge=1),
    major_id: int | None = Query(default=None, ge=1),
    class_id: int | None = Query(default=None, ge=1),
    category: directory_service.DirectoryCategory = "all",
    relation: directory_service.DirectoryRelation | None = None,
) -> Page[MemberBrief]:
    try:
        return directory_service.list_members(
            db, current_user, q, page, page_size, discover=discover, entry_year=entry_year,
            college_id=college_id, department_id=department_id, major_id=major_id, class_id=class_id,
            category=category, relation=relation,
        )
    except directory_service.DirectoryProfileIncomplete as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/members/{member_id}", response_model=MemberDetail)
def get_member(
    member_id: int, current_user: CurrentUser, db: DbSession
) -> MemberDetail:
    member = directory_service.get_member(db, current_user, member_id)
    if member is None:
        # Do not reveal whether the target exists outside the viewer's scope.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="无权查看或成员不存在"
        )
    return member
