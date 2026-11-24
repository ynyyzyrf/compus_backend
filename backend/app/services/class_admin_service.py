from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import OrgType, Role, Status
from app.models.organization import ClassAdministrator, Membership, Organization
from app.models.user import User
from app.services.org_tree import load_org_tree


def get_class(db: Session, class_id: int, *, lock: bool = False, active: bool = False) -> Organization:
    org = db.get(Organization, class_id, with_for_update=lock)
    if org is None or org.type != OrgType.CLASS:
        raise HTTPException(404, "班级不存在")
    if active and load_org_tree(db).school_for_class(class_id) is None:
        raise HTTPException(400, "请选择有效的班级")
    return org


def managed_class_ids(db: Session, user_id: int) -> set[int]:
    tree = load_org_tree(db)
    return {class_id for class_id in db.scalars(select(ClassAdministrator.organization_id).where(
        ClassAdministrator.user_id == user_id,
    )) if tree.school_for_class(class_id) is not None}


def require_can_review(db: Session, reviewer: User, applicant_id: int) -> None:
    if reviewer.role == Role.SUPER_ADMIN:
        return
    applicant = db.get(User, applicant_id, with_for_update=True)
    if applicant is None or applicant.pending_class_id is None:
        raise HTTPException(404, "待审核申请不存在")
    assignment = db.get(ClassAdministrator, (applicant.pending_class_id, reviewer.id), with_for_update=True)
    if assignment is None or applicant.pending_class_id not in managed_class_ids(db, reviewer.id):
        raise HTTPException(403, "只能审核所管理班级的加入申请")


def administrator_list(db: Session, class_id: int) -> dict:
    org = get_class(db, class_id)
    users = db.scalars(select(User).join(ClassAdministrator, ClassAdministrator.user_id == User.id)
                       .where(ClassAdministrator.organization_id == class_id).order_by(User.id)).all()
    return {"class_id": org.id, "class_name": org.name,
            "items": [{"id": user.id, "name": user.name, "status": user.status} for user in users]}


def candidates(db: Session, class_id: int, q: str, page: int, page_size: int) -> dict:
    get_class(db, class_id, active=True)
    assigned = select(ClassAdministrator.user_id).where(ClassAdministrator.organization_id == class_id)
    query = select(User).where(User.status == Status.ACTIVE, User.role != Role.SUPER_ADMIN, User.id.not_in(assigned))
    if q.strip():
        query = query.where(User.name.icontains(q.strip(), autoescape=True))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(query.order_by(User.id).offset((page - 1) * page_size).limit(page_size)).all()
    ids = [user.id for user in users]
    memberships = dict(db.execute(select(Membership.user_id, Membership.organization_id).where(
        Membership.user_id.in_(ids), Membership.is_primary.is_(True),
    )).all())
    tree = load_org_tree(db)
    return {"items": [{"id": user.id, "name": user.name, "org_path": tree.path_name(memberships.get(user.id))
                        if memberships.get(user.id) in tree.nodes else ""} for user in users],
            "total": total, "page": page, "page_size": page_size}


def add_administrator(db: Session, class_id: int, user_id: int) -> dict:
    get_class(db, class_id, lock=True, active=True)
    user = db.get(User, user_id, with_for_update=True)
    if user is None or user.status != Status.ACTIVE:
        raise HTTPException(400, "请选择已启用的用户")
    if user.role == Role.SUPER_ADMIN:
        raise HTTPException(400, "超级管理员已拥有全部审核权限，无需重复分配")
    if db.get(ClassAdministrator, (class_id, user_id)) is None:
        db.add(ClassAdministrator(organization_id=class_id, user_id=user_id))
    user.role = Role.CLASS_ADMIN
    db.commit()
    return administrator_list(db, class_id)


def remove_administrator(db: Session, class_id: int, user_id: int) -> dict:
    get_class(db, class_id, lock=True)
    user = db.get(User, user_id, with_for_update=True)
    assignment = db.get(ClassAdministrator, (class_id, user_id))
    if assignment is not None:
        db.delete(assignment)
        db.flush()
    if user is not None and user.role == Role.CLASS_ADMIN and not db.scalar(
        select(ClassAdministrator.user_id).where(ClassAdministrator.user_id == user_id).limit(1)
    ):
        user.role = Role.USER
    db.commit()
    return administrator_list(db, class_id)
