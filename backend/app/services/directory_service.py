"""Directory reads, always filtered through the permission scope."""

from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import OrgType, Status
from app.models.organization import Membership
from app.models.user import User
from app.schemas.common import Page
from app.schemas.directory import (
    DirectoryTreeOut,
    MemberBrief,
    MemberDetail,
    OrgNodeOut,
)
from app.services.directory_permission import get_primary_class_id, readable_scope
from app.services.name_display import display_name_en
from app.services.org_tree import load_org_tree, normalize_org_keyword
from app.services.profile_visibility import accepted_peers, allows

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DirectoryCategory = Literal["all", "city", "profession"]
DirectoryRelation = Literal["class", "year", "department", "college"]


class DirectoryProfileIncomplete(Exception):
    pass


def alumni_school(db, tree, user_id: int) -> int | None:
    class_id = get_primary_class_id(db, user_id)
    return tree.school_for_class(class_id) if class_id is not None else None


def can_find_alumnus(db, tree, viewer, target, target_class_id: int) -> bool:
    """A contact request requires an approved sender and a visible recipient."""
    viewer_class = get_primary_class_id(db, viewer.id)
    school_id = tree.school_for_class(viewer_class) if viewer_class is not None else None
    target_school = tree.school_for_class(target_class_id)
    if school_id is None or target_school is None or target.status != Status.ACTIVE or target.basic_visibility == "private":
        return False
    return (target.basic_visibility == "classmates" and target_class_id == viewer_class) or (
        target.alumni_discoverable and school_id == target_school
    )


def directory_tree(db: Session, user: User) -> DirectoryTreeOut:
    tree = load_org_tree(db)
    scope = readable_scope(db, tree, user)

    if not scope.class_ids:
        return DirectoryTreeOut(nodes=[], scope_level=scope.scope_level)

    # Primary-member count per class, only inside the open subtree.
    rows = db.execute(
        select(Membership.organization_id, func.count())
        .where(
            Membership.is_primary.is_(True),
            Membership.organization_id.in_(scope.class_ids),
        )
        .group_by(Membership.organization_id)
    ).all()
    class_counts = {org_id: count for org_id, count in rows}

    nodes: list[OrgNodeOut] = []
    for nid in sorted(
        scope.visible_node_ids,
        key=lambda x: (tree.nodes[x].sort_order, tree.nodes[x].id),
    ):
        node = tree.nodes[nid]
        subtree_classes = tree.classes_under(tree.descendants(nid)) & scope.class_ids
        member_count = sum(class_counts.get(cid, 0) for cid in subtree_classes)
        nodes.append(
            OrgNodeOut(
                id=node.id,
                name=node.name,
                type=node.type,
                parent_id=node.parent_id,
                sort_order=node.sort_order,
                member_count=member_count,
                entry_year=node.entry_year,
            )
        )
    return DirectoryTreeOut(nodes=nodes, scope_level=scope.scope_level)


def list_members(
    db: Session, user: User, q: str | None, page: int, page_size: int,
    *, discover: bool = False, entry_year: int | None = None,
    college_id: int | None = None, department_id: int | None = None,
    major_id: int | None = None, class_id: int | None = None,
    category: DirectoryCategory = "all",
    relation: DirectoryRelation | None = None,
) -> Page[MemberBrief]:
    tree = load_org_tree(db)
    scope = readable_scope(db, tree, user)

    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    keyword = (q or "").strip()
    filters = {
        "college": college_id, "department": department_id,
        "major": major_id, "class": class_id,
    }
    viewer_class = get_primary_class_id(db, user.id)
    school_id = tree.school_for_class(viewer_class) if viewer_class is not None else None
    friends = accepted_peers(db, user.id)
    same_class = Membership.organization_id == viewer_class if school_id is not None else False
    friend = User.id.in_(friends)
    basic_visibility = or_(
        User.id == user.id,
        (User.basic_visibility == "classmates") & or_(same_class, friend),
        (User.basic_visibility == "friends") & friend,
    )
    discoverable = False
    search_classes = scope.class_ids
    visibility = Membership.organization_id.in_(scope.class_ids)
    if discover and category == "all" and school_id is not None and (keyword or entry_year or relation or any(filters.values())):
        same_school = tree.classes_under(tree.descendants(school_id))
        search_classes = scope.class_ids | same_school
        discoverable = (
            User.alumni_discoverable.is_(True) & (User.basic_visibility != "private") & Membership.organization_id.in_(same_school)
        )
        visibility = or_(visibility, discoverable)
    if not search_classes:
        return Page(items=[], total=0, page=page, page_size=page_size)

    if relation:
        chain = {tree.nodes[node].type: node for node in tree.ancestors(viewer_class)} if school_id is not None else {}
        if relation == "year" and chain:
            year = tree.nodes[viewer_class].entry_year
            matches = {cid for cid in search_classes if year is not None and tree.nodes[cid].entry_year == year and tree.school_for_class(cid) == school_id}
        else:
            node = chain.get({"class": OrgType.CLASS, "department": OrgType.DEPARTMENT, "college": OrgType.COLLEGE}.get(relation))
            matches = tree.classes_under(tree.descendants(node)) if node is not None else set()
        search_classes &= matches

    stmt = (
        select(User, Membership.organization_id)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.is_primary.is_(True),
            visibility,
            or_(basic_visibility, discoverable),
            User.status == Status.ACTIVE,
        )
    )

    if category != "all":
        field, label = (User.city, "所在城市") if category == "city" else (User.profession, "专业领域")
        value = (getattr(user, field.key) or "").strip()
        if not value:
            raise DirectoryProfileIncomplete(f"请先在个人名片填写{label}")
        stmt = stmt.where(User.id != user.id, func.lower(func.trim(field)) == func.lower(value))
        for audience in (User.basic_visibility, User.details_visibility):
            stmt = stmt.where(or_(
                (audience == "classmates") & or_(same_class, friend),
                (audience == "friends") & friend,
            ))

    for node_type, node_id in filters.items():
        if node_id is not None:
            node = tree.nodes.get(node_id)
            hits = tree.classes_under(tree.descendants(node_id)) if node and node.type == node_type else set()
            search_classes = search_classes & hits
    if entry_year is not None:
        search_classes = {cid for cid in search_classes if tree.nodes[cid].entry_year == entry_year}
    stmt = stmt.where(Membership.organization_id.in_(search_classes))
    for term in normalize_org_keyword(keyword).split():
        org_hits = tree.find_by_path_keyword(term) & search_classes
        stmt = stmt.where(
            or_(
                User.name.icontains(term, autoescape=True),
                basic_visibility & User.name_en.icontains(term, autoescape=True),
                Membership.organization_id.in_(org_hits),
            )
        )

    total = db.execute(
        select(func.count())
        .select_from(User)
        .join(Membership, Membership.user_id == User.id)
        .where(stmt.whereclause)
    ).scalar_one()

    rows = db.execute(
        stmt.order_by(Membership.organization_id, User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        MemberBrief(
            id=member.id,
            name=member.name,
            avatar_url=member.avatar_url,
            class_id=class_id,
            org_path=tree.path_name(class_id),
            can_view_profile=allows(member.basic_visibility, own=member.id == user.id, same_class=class_id == viewer_class, friend=member.id in friends),
        )
        for member, class_id in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


def get_member(db: Session, user: User, member_id: int) -> MemberDetail | None:
    tree = load_org_tree(db)

    target = db.get(User, member_id)
    if target is None or target.status != Status.ACTIVE:
        return None

    class_id = db.execute(
        select(Membership.organization_id)
        .where(
            Membership.user_id == member_id,
            Membership.is_primary.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()

    viewer_class = get_primary_class_id(db, user.id)
    relationship = {
        "own": member_id == user.id,
        "same_class": class_id is not None and class_id == viewer_class and tree.school_for_class(class_id) is not None,
        "friend": member_id in accepted_peers(db, user.id),
    }
    if not allows(target.basic_visibility, **relationship):
        return None

    contact = allows(target.contact_visibility, **relationship)
    details = allows(target.details_visibility, **relationship)
    return MemberDetail(
        id=target.id,
        name=target.name,
        avatar_url=target.avatar_url,
        class_id=class_id,
        org_path=tree.path_name(class_id) if class_id in tree.nodes else "",
        phone=target.phone if contact else None,
        wechat_id=target.wechat_id if contact else None,
        email=target.email if contact else None,
        name_en=target.name_en,
        name_en_display=display_name_en(target.name, target.name_en),
        is_friend=relationship["friend"],
        **{field: getattr(target, field) for field in (
            "profession", "profession_en", "position", "company_name", "company_address", "company_founded_at",
            "bio", "business_description", "referrals_needed", "personal_experience", "resources_offered",
            "chamber_chapter", "chamber_member_no", "chamber_join_date", "chamber_score",
        )} if details else {},
    )
