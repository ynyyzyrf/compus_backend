"""Admin member / org / permission / dashboard services."""

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityCheckin, ActivitySignup
from app.models.enums import (
    ActivityStatus,
    Role,
    SignupStatus,
    Status,
)
from app.models.organization import (
    DirectoryPermission,
    Membership,
    Organization,
)
from app.models.user import User
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

MAX_PAGE_SIZE = 200


# ===== members =====


def list_members(
    db: Session,
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    college_id: int | None = None,
    department_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[User, int | None, str]], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)

    if college_id or department_id:
        # restrict to classes under the given node
        tree = load_org_tree(db)
        root = college_id or department_id
        target_classes = (
            {root} if tree.nodes[root].type == "class"
            else tree.classes_under(tree.descendants(root))
        )
        if not target_classes:
            return [], 0
        member_user_ids = set(
            db.scalars(
                select(Membership.user_id).where(
                    Membership.organization_id.in_(target_classes),
                    Membership.is_primary.is_(True),
                )
            ).all()
        )
        if not member_user_ids:
            return [], 0
        stmt = stmt.where(User.id.in_(member_user_ids))

    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (User.name.ilike(like))
            | (User.phone.ilike(like))
            | (User.wechat_id.ilike(like))
            | (User.company_name.ilike(like))
            | (User.position.ilike(like))
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    tree = load_org_tree(db)
    result: list[tuple[User, int | None, str]] = []
    for user in rows:
        class_id = get_primary_class_id(db, user.id)
        result.append((user, class_id, tree.path_name(class_id) if class_id else ""))
    return result, total


def update_member(db: Session, user_id: int, payload) -> User | None:
    u = db.get(User, user_id)
    if u is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(u, key, value)
    db.commit()
    db.refresh(u)
    return u


def set_member_status(db: Session, user_id: int, status_value: str) -> User | None:
    u = db.get(User, user_id)
    if u is None:
        return None
    u.status = status_value
    db.commit()
    db.refresh(u)
    return u


# ===== organizations =====


def list_org_tree(db: Session, include_disabled: bool = True) -> list[Organization]:
    stmt = select(Organization).order_by(Organization.sort_order, Organization.id)
    if not include_disabled:
        stmt = stmt.where(Organization.status == Status.ACTIVE)
    return list(db.scalars(stmt))


def create_org(db: Session, payload) -> Organization:
    if payload.parent_id is not None:
        parent = db.get(Organization, payload.parent_id)
        if parent is None:
            raise ValueError("父節點不存在")
    o = Organization(
        name=payload.name,
        type=payload.type,
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def update_org(db: Session, org_id: int, payload) -> Organization | None:
    o = db.get(Organization, org_id)
    if o is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data:
        new_parent = data["parent_id"]
        if new_parent is not None:
            if new_parent == org_id:
                raise ValueError("不能將自己設為父節點")
            # also prevent moving under own descendants (cycle)
            tree = load_org_tree(db)
            descendants = tree.descendants(org_id)
            if new_parent in descendants:
                raise ValueError("不能將節點移到自己的子節點下")
    for key, value in data.items():
        setattr(o, key, value)
    db.commit()
    db.refresh(o)
    return o


def delete_org(db: Session, org_id: int) -> bool:
    o = db.get(Organization, org_id)
    if o is None:
        return False
    # soft-delete: only if no users attached
    has_member = db.execute(
        select(Membership.id).where(Membership.organization_id == org_id).limit(1)
    ).first()
    if has_member:
        o.status = Status.DISABLED
        db.commit()
    else:
        db.delete(o)
        db.commit()
    return True


# ===== directory permissions =====


def list_directory_permissions(db: Session) -> list[DirectoryPermission]:
    return list(db.scalars(select(DirectoryPermission)))


def batch_update_permissions(
    db: Session, items: list[dict]
) -> list[DirectoryPermission]:
    """Replace (upsert) the given permission rows. Other rows are untouched.

    Each item: ``{organization_id, scope_type, is_enabled}``.
    """
    out: list[DirectoryPermission] = []
    for it in items:
        org_id = it["organization_id"]
        row = db.scalars(
            select(DirectoryPermission).where(
                DirectoryPermission.organization_id == org_id
            )
        ).first()
        if row is None:
            row = DirectoryPermission(
                organization_id=org_id,
                scope_type=it["scope_type"],
                is_enabled=it["is_enabled"],
            )
            db.add(row)
        else:
            row.scope_type = it["scope_type"]
            row.is_enabled = it["is_enabled"]
        out.append(row)
    db.commit()
    for r in out:
        db.refresh(r)
    return out


# ===== dashboard =====


def dashboard_stats(db: Session) -> dict:
    orgs = list(db.scalars(select(Organization)).all())
    college = sum(1 for o in orgs if o.type == "college")
    dept = sum(1 for o in orgs if o.type == "department")
    klass = sum(1 for o in orgs if o.type == "class")

    member_total = db.execute(select(func.count(User.id))).scalar_one()
    active_member_total = db.execute(
        select(func.count(User.id)).where(User.status == Status.ACTIVE)
    ).scalar_one()

    activities = list(
        db.scalars(
            select(Activity).where(Activity.status != ActivityStatus.DRAFT)
        )
    )
    now = datetime.now(timezone.utc)
    signing = 0
    ongoing = 0
    finished_for_rate = []
    for a in activities:
        s = a.start_at
        e = a.end_at
        if s.tzinfo is None:
            s = s.replace(tzinfo=timezone.utc)
            e = e.replace(tzinfo=timezone.utc)
        if s <= now <= e:
            ongoing += 1
        elif now < s:
            signing += 1
        if e < now:
            finished_for_rate.append(a)

    # recent checkin rate: average over last 3 finished activities
    rate = 0.0
    recent = sorted(
        finished_for_rate, key=lambda x: x.end_at, reverse=True
    )[:3]
    if recent:
        total_signups = 0
        total_checkins = 0
        for a in recent:
            signed = db.execute(
                select(func.count(ActivitySignup.id)).where(
                    ActivitySignup.activity_id == a.id,
                    ActivitySignup.status == SignupStatus.SIGNED,
                )
            ).scalar_one()
            checked = db.execute(
                select(func.count(ActivityCheckin.id)).where(
                    ActivityCheckin.activity_id == a.id,
                )
            ).scalar_one()
            total_signups += signed
            total_checkins += checked
        rate = (total_checkins / total_signups) if total_signups else 0.0

    return {
        "member_total": member_total,
        "active_member_total": active_member_total,
        "college_count": college,
        "department_count": dept,
        "class_count": klass,
        "signing_activity_total": signing,
        "ongoing_activity_total": ongoing,
        "recent_checkin_rate": rate,
    }
