from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.deps import AffiliationReviewer, DbSession, SuperAdmin
from app.models.enums import Role
from app.models.organization import Membership, Organization
from app.models.user import User
from app.schemas.admin import (
    DashboardStats,
    DirectoryPermissionBatchUpdate,
    DirectoryPermissionOut,
    MemberAdminOut,
    MemberListPage,
    MemberUpdate,
    OrgNodeAdminOut,
    OrgNodeCreate,
    OrgNodeUpdate,
)
from app.services import admin_service, affiliation_service, class_admin_service
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

router = APIRouter(prefix="/admin", tags=["admin"])


# ===== dashboard =====


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(_: SuperAdmin, db: DbSession) -> DashboardStats:
    return DashboardStats(**admin_service.dashboard_stats(db))


# ===== members =====


@router.get("/affiliation-requests")
def list_affiliation_requests(reviewer: AffiliationReviewer, db: DbSession) -> list[dict]:
    tree = load_org_tree(db)
    query = select(User).where(User.pending_class_id.is_not(None))
    if reviewer.role != Role.SUPER_ADMIN:
        query = query.where(User.pending_class_id.in_(class_admin_service.managed_class_ids(db, reviewer.id)))
    users = db.scalars(query.order_by(User.affiliation_requested_at, User.id)).all()
    return [
        {
            "user_id": user.id,
            "name": user.name,
            "verified_phone": user.verified_phone if reviewer.role == Role.SUPER_ADMIN else None,
            "class_id": user.pending_class_id,
            "org_path": affiliation_service.full_path(tree, user.pending_class_id) if user.pending_class_id in tree.nodes else "班级已失效",
            "requested_at": user.affiliation_requested_at,
        }
        for user in users
    ]


@router.post("/affiliation-requests/{user_id}/approve")
def approve_affiliation_request(user_id: int, reviewer: AffiliationReviewer, db: DbSession) -> dict:
    class_admin_service.require_can_review(db, reviewer, user_id)
    affiliation_service.review_affiliation(db, user_id, approve=True)
    return {"ok": True}


@router.post("/affiliation-requests/{user_id}/reject")
def reject_affiliation_request(user_id: int, reviewer: AffiliationReviewer, db: DbSession) -> dict:
    class_admin_service.require_can_review(db, reviewer, user_id)
    affiliation_service.review_affiliation(db, user_id, approve=False)
    return {"ok": True}


@router.get("/missing-classes")
def list_missing_classes(_: SuperAdmin, db: DbSession) -> list[dict]:
    users = db.scalars(select(User).where(User.missing_class_note.is_not(None)).order_by(User.id))
    return [{"user_id": user.id, "name": user.name, "note": user.missing_class_note} for user in users]


@router.post("/missing-classes/{user_id}/resolve", status_code=204)
def resolve_missing_class(user_id: int, _: SuperAdmin, db: DbSession):
    user = db.get(User, user_id, with_for_update=True)
    if user is None:
        raise HTTPException(404, "校友不存在")
    user.missing_class_note = None
    db.commit()


def _member_view(db, user, class_id: int | None, org_path: str) -> MemberAdminOut:
    o_name = db.get(Organization, class_id).name if class_id else None
    return MemberAdminOut(
        id=user.id,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        status=user.status,
        openid=user.openid,
        unionid=user.unionid,
        phone=user.phone,
        wechat_id=user.wechat_id,
        email=user.email,
        name_en=user.name_en,
        profession=user.profession,
        profession_en=user.profession_en,
        position=user.position,
        company_name=user.company_name,
        company_address=user.company_address,
        company_founded_at=user.company_founded_at,
        bio=user.bio,
        business_description=user.business_description,
        referrals_needed=user.referrals_needed,
        personal_experience=user.personal_experience,
        resources_offered=user.resources_offered,
        chamber_chapter=user.chamber_chapter,
        chamber_member_no=user.chamber_member_no,
        chamber_join_date=user.chamber_join_date,
        chamber_score=user.chamber_score,
        primary_class_id=class_id,
        primary_class_name=o_name,
        primary_org_path=org_path,
    )


@router.get("/members", response_model=MemberListPage)
def list_members(
    _: SuperAdmin,
    db: DbSession,
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    college_id: int | None = None,
    department_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> MemberListPage:
    rows, total = admin_service.list_members(
        db,
        q=q,
        role=role,
        status=status,
        college_id=college_id,
        department_id=department_id,
        page=page,
        page_size=page_size,
    )
    items = [_member_view(db, u, cid, path) for (u, cid, path) in rows]
    return MemberListPage(items=items, total=total, page=page, page_size=page_size)


@router.put("/members/{user_id}", response_model=MemberAdminOut)
def update_member(
    user_id: int, payload: MemberUpdate, _: SuperAdmin, db: DbSession
) -> MemberAdminOut:
    try:
        user = admin_service.update_member(db, user_id, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")
    class_id = get_primary_class_id(db, user_id)
    tree = load_org_tree(db)
    return _member_view(
        db, user, class_id, tree.path_name(class_id) if class_id else ""
    )


@router.post("/members/{user_id}/status", response_model=MemberAdminOut)
def set_member_status(
    user_id: int,
    payload: dict,  # noqa: F821 -- body parsed loosely here for brevity
    _: SuperAdmin,
    db: DbSession,
) -> MemberAdminOut:
    new_status = payload.get("status")
    if new_status not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="status 必须为 active 或 disabled")
    user = admin_service.set_member_status(db, user_id, new_status)
    if user is None:
        raise HTTPException(status_code=404, detail="成员不存在")
    class_id = get_primary_class_id(db, user_id)
    tree = load_org_tree(db)
    return _member_view(
        db, user, class_id, tree.path_name(class_id) if class_id else ""
    )


# ===== organizations =====


class ClassAdministratorInput(BaseModel):
    user_id: int = Field(gt=0)


@router.get("/organizations/{class_id}/class-admins")
def list_class_administrators(class_id: int, _: SuperAdmin, db: DbSession) -> dict:
    return class_admin_service.administrator_list(db, class_id)


@router.get("/organizations/{class_id}/class-admin-candidates")
def class_administrator_candidates(class_id: int, _: SuperAdmin, db: DbSession,
                                   q: str = Query(default="", max_length=80),
                                   page: int = Query(default=1, ge=1),
                                   page_size: int = Query(default=20, ge=1, le=100)) -> dict:
    return class_admin_service.candidates(db, class_id, q, page, page_size)


@router.post("/organizations/{class_id}/class-admins")
def add_class_administrator(class_id: int, payload: ClassAdministratorInput, _: SuperAdmin, db: DbSession) -> dict:
    return class_admin_service.add_administrator(db, class_id, payload.user_id)


@router.delete("/organizations/{class_id}/class-admins/{user_id}")
def remove_class_administrator(class_id: int, user_id: int, _: SuperAdmin, db: DbSession) -> dict:
    return class_admin_service.remove_administrator(db, class_id, user_id)


@router.get("/organizations", response_model=list[OrgNodeAdminOut])
def list_organizations(_: SuperAdmin, db: DbSession) -> list[OrgNodeAdminOut]:
    rows = admin_service.list_org_tree(db)
    # member counts per node (only counting active users in primary class)
    member_counts: dict[int, int] = {}
    for r in rows:
        if r.type != "class":
            continue
        c = db.execute(
            select(func.count(Membership.id)).where(
                Membership.organization_id == r.id,
                Membership.is_primary.is_(True),
            )
        ).scalar_one()
        member_counts[r.id] = c
    return [
        OrgNodeAdminOut(
            id=o.id,
            name=o.name,
            type=o.type,
            parent_id=o.parent_id,
            sort_order=o.sort_order,
            status=o.status,
            entry_year=o.entry_year,
            member_count=member_counts.get(o.id, 0),
        )
        for o in rows
    ]


@router.post("/organizations", response_model=OrgNodeAdminOut, status_code=201)
def create_organization(
    payload: OrgNodeCreate, _: SuperAdmin, db: DbSession
) -> OrgNodeAdminOut:
    try:
        o = admin_service.create_org(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return OrgNodeAdminOut(
        id=o.id,
        name=o.name,
        type=o.type,
        parent_id=o.parent_id,
        sort_order=o.sort_order,
        status=o.status,
        entry_year=o.entry_year,
        member_count=0,
    )


@router.put("/organizations/{org_id}", response_model=OrgNodeAdminOut)
def update_organization(
    org_id: int, payload: OrgNodeUpdate, _: SuperAdmin, db: DbSession
) -> OrgNodeAdminOut:
    try:
        o = admin_service.update_org(db, org_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if o is None:
        raise HTTPException(status_code=404, detail="节点不存在")
    return OrgNodeAdminOut(
        id=o.id,
        name=o.name,
        type=o.type,
        parent_id=o.parent_id,
        sort_order=o.sort_order,
        status=o.status,
        entry_year=o.entry_year,
        member_count=0,
    )


@router.delete("/organizations/{org_id}", status_code=204)
def delete_organization(org_id: int, _: SuperAdmin, db: DbSession) -> None:
    try:
        deleted = admin_service.delete_org(db, org_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="节点不存在")


# ===== directory permissions =====


@router.get("/directory-permissions", response_model=list[DirectoryPermissionOut])
def list_permissions(_: SuperAdmin, db: DbSession) -> list[DirectoryPermissionOut]:
    tree = load_org_tree(db)
    rows = admin_service.list_directory_permissions(db)
    by_id = {p.organization_id: p for p in rows}
    out: list[DirectoryPermissionOut] = []
    for o in db.scalars(
        select(Organization).order_by(Organization.sort_order)
    ):
        if o.type not in {"college", "department"}:
            continue
        p = by_id.get(o.id)
        out.append(
            DirectoryPermissionOut(
                organization_id=o.id,
                organization_name=o.name,
                organization_type=o.type,
                scope_type=p.scope_type if p else (
                    "college" if o.type == "college" else "department"
                ),
                is_enabled=p.is_enabled if p else False,
            )
        )
    return out


@router.put("/directory-permissions", response_model=list[DirectoryPermissionOut])
def update_permissions(
    payload: DirectoryPermissionBatchUpdate, _: SuperAdmin, db: DbSession
) -> list[DirectoryPermissionOut]:
    admin_service.batch_update_permissions(
        db, [p.model_dump() for p in payload.permissions]
    )
    return list_permissions(_=None, db=db)  # type: ignore[arg-type]
