"""Admin member / org / permission / dashboard services."""

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityCheckin, ActivitySignup
from app.models.enums import (
    ActivityStatus,
    Role,
    SignupStatus,
    Status,
)
from app.models.organization import (
    ClassAdministrator,
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
    u = db.get(User, user_id, with_for_update=True)
    if u is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    if data.get("role") == Role.CLASS_ADMIN and not db.scalar(
        select(ClassAdministrator.user_id).where(ClassAdministrator.user_id == user_id).limit(1)
    ):
        raise ValueError("请在组织架构中分配班级管理员")
    if data.get("role") in {Role.USER, Role.SUPER_ADMIN}:
        db.execute(delete(ClassAdministrator).where(ClassAdministrator.user_id == user_id))
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


ORG_PARENTS = {
    "school": {None},
    "college": {"school"},
    "department": {"college"},
    "major": {"department"},
    "class": {"department", "major"},
}


def validate_org(
    db: Session, node_type: str, parent_id: int | None, name: str,
    entry_year: int | None, current_id: int | None = None,
) -> str:
    name = name.strip()
    if not name:
        raise ValueError("请填写组织名称")
    parent = None
    if parent_id is not None:
        parent = db.get(Organization, parent_id, with_for_update=True)
        if parent is None or parent.status != Status.ACTIVE:
            raise ValueError("上级组织不存在或已停用")
    if (parent.type if parent else None) not in ORG_PARENTS[node_type]:
        raise ValueError("请选择正确的上级组织")
    if entry_year is not None and node_type != "class":
        raise ValueError("只有班级可以设置入学年份")
    matches = select(Organization.id).where(
        Organization.type == node_type,
        Organization.parent_id == parent_id,
        Organization.entry_year == entry_year,
        func.lower(Organization.name) == name.lower(),
    )
    if current_id is not None:
        matches = matches.where(Organization.id != current_id)
    if db.scalar(matches.limit(1)) is not None:
        raise ValueError("该上级组织下已存在同名、同入学年份的节点")
    return name


def create_org(db: Session, payload) -> Organization:
    name = validate_org(db, payload.type, payload.parent_id, payload.name, payload.entry_year)
    o = Organization(
        name=name,
        type=payload.type,
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
        entry_year=payload.entry_year,
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
    new_parent = data.get("parent_id", o.parent_id)
    if new_parent != o.parent_id and o.type == "class":
        previous = db.get(Organization, o.parent_id) if o.parent_id is not None else None
        destination = db.get(Organization, new_parent) if new_parent is not None else None
        department_id = previous.parent_id if previous and previous.type == "major" else o.parent_id
        target_department_id = destination.parent_id if destination and destination.type == "major" else new_parent
        if department_id != target_department_id:
            raise ValueError("班级只能在所属系内调整专业")
    if {"name", "parent_id", "entry_year"} & data.keys():
        if data.get("name", o.name) is None:
            raise ValueError("请填写组织名称")
        data["name"] = validate_org(
            db, o.type, new_parent, data.get("name", o.name),
            data.get("entry_year", o.entry_year), o.id,
        )
    for key, value in data.items():
        setattr(o, key, value)
    db.commit()
    db.refresh(o)
    return o


def delete_org(db: Session, org_id: int) -> bool:
    o = db.get(Organization, org_id)
    if o is None:
        return False
    if db.scalar(select(Organization.id).where(Organization.parent_id == org_id).limit(1)) is not None:
        raise ValueError("请先处理此节点下的组织")
    if db.scalar(select(User.id).where(User.pending_class_id == org_id).limit(1)) is not None:
        raise ValueError("请先处理该班级的入组申请")
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
