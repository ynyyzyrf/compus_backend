"""Apply for and approve a primary class without granting access early."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Membership
from app.models.user import User
from app.schemas.profile import MyAffiliation
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree


def valid_class(tree, class_id: int) -> bool:
    chain = tree.ancestors(class_id)
    return len(chain) == 4 and [tree.nodes[n].type for n in chain] == [
        "class", "department", "college", "school"
    ] and tree.nodes[chain[-1]].parent_id is None


def full_path(tree, class_id: int) -> str:
    return " · ".join(tree.nodes[node_id].name for node_id in reversed(tree.ancestors(class_id)))


def my_affiliation(db: Session, user: User) -> MyAffiliation:
    tree = load_org_tree(db)
    class_id = get_primary_class_id(db, user.id)
    pending_id = user.pending_class_id
    return MyAffiliation(
        class_id=class_id if class_id in tree.nodes else None,
        org_path=tree.path_name(class_id) if class_id in tree.nodes else "",
        pending_class_id=pending_id if pending_id in tree.nodes else None,
        pending_org_path=full_path(tree, pending_id) if pending_id in tree.nodes else "",
    )


def request_affiliation(db: Session, user_id: int, class_id: int, name: str | None = None) -> MyAffiliation:
    user = db.scalars(select(User).where(User.id == user_id).with_for_update()).one()
    if get_primary_class_id(db, user_id) is not None:
        raise HTTPException(status_code=409, detail="已加入組織，請聯絡管理員修改")
    tree = load_org_tree(db)
    if not valid_class(tree, class_id):
        raise HTTPException(status_code=400, detail="請選擇有效的學校、學院、系和班級")
    if user.pending_class_id and user.pending_class_id != class_id:
        raise HTTPException(status_code=409, detail="已有待審核申請，請等待管理員處理")
    if name is not None:
        user.name = name
    if not user.pending_class_id:
        user.pending_class_id = class_id
        user.affiliation_requested_at = datetime.now(UTC)
    if db.is_modified(user):
        db.commit()
    return my_affiliation(db, user)


def review_affiliation(db: Session, user_id: int, approve: bool) -> MyAffiliation:
    user = db.scalars(select(User).where(User.id == user_id).with_for_update()).one_or_none()
    if user is None or user.pending_class_id is None:
        raise HTTPException(status_code=404, detail="待審核申請不存在")
    class_id = user.pending_class_id
    tree = load_org_tree(db)
    if approve:
        if not valid_class(tree, class_id):
            raise HTTPException(status_code=409, detail="班級已失效，請退回申請")
        if get_primary_class_id(db, user_id) is not None:
            raise HTTPException(status_code=409, detail="用戶已有主要班級，請先核對")
        membership = db.scalars(select(Membership).where(
            Membership.user_id == user_id, Membership.organization_id == class_id
        )).first()
        if membership:
            membership.is_primary = True
        else:
            db.add(Membership(user_id=user_id, organization_id=class_id, is_primary=True))
    user.pending_class_id = None
    user.affiliation_requested_at = None
    db.commit()
    return my_affiliation(db, user)
