"""Compute the set of organization nodes / members a user may read.

Rule model (PRD §8), deliberately simple:

* The viewer's primary membership is a class. Walking parent_id gives the
  class -> department -> college chain.
* A directory_permissions row enabled on the COLLEGE node opens the whole
  college; enabled on the DEPARTMENT node opens the whole department;
  otherwise only the viewer's own CLASS is readable (default on).
* A higher-level rule covers every descendant, so nothing is configured per
  class. Super admin reads everything.

All read endpoints filter through :func:`readable_scope`; the frontend never
owns authorization.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DirectoryScope, OrgType, Role
from app.models.organization import DirectoryPermission, Membership
from app.models.user import User
from app.services.org_tree import OrgTree


@dataclass
class ReadableScope:
    scope_node_id: int | None          # node whose subtree is open
    scope_level: str                   # class / department / college / all
    visible_node_ids: set[int]         # nodes to render in the tree (+ancestors)
    class_ids: set[int]                # class nodes whose members are readable


def get_primary_class_id(db: Session, user_id: int) -> int | None:
    row = db.execute(
        select(Membership.organization_id)
        .where(Membership.user_id == user_id, Membership.is_primary.is_(True))
        .limit(1)
    ).scalar_one_or_none()
    return row


def _enabled_rules(db: Session) -> dict[int, str]:
    rows = db.scalars(
        select(DirectoryPermission).where(DirectoryPermission.is_enabled.is_(True))
    )
    return {r.organization_id: r.scope_type for r in rows}


def readable_scope(db: Session, tree: OrgTree, user: User) -> ReadableScope:
    all_nodes = set(tree.nodes.keys())

    if user.role == Role.SUPER_ADMIN:
        return ReadableScope(
            scope_node_id=next(
                (nid for nid, n in tree.nodes.items() if n.type == OrgType.SCHOOL),
                None,
            ),
            scope_level="all",
            visible_node_ids=all_nodes,
            class_ids=tree.classes_under(all_nodes),
        )

    class_id = get_primary_class_id(db, user.id)
    if class_id is None or class_id not in tree.nodes:
        return ReadableScope(None, "none", set(), set())

    chain_ids = tree.ancestors(class_id)
    chain_types = {tree.nodes[nid].type: nid for nid in chain_ids}
    college_id = chain_types.get(OrgType.COLLEGE)
    department_id = chain_types.get(OrgType.DEPARTMENT)

    rules = _enabled_rules(db)

    if (
        college_id is not None
        and rules.get(college_id) == DirectoryScope.COLLEGE
    ):
        scope_id, level = college_id, DirectoryScope.COLLEGE
    elif (
        department_id is not None
        and rules.get(department_id) == DirectoryScope.DEPARTMENT
    ):
        scope_id, level = department_id, DirectoryScope.DEPARTMENT
    else:
        # Default: same-class readable is always on (PRD §8.2).
        scope_id, level = class_id, DirectoryScope.CLASS

    subtree = tree.descendants(scope_id)
    visible = set(subtree)
    visible.update(chain_ids)  # ancestor containers needed to navigate the tree

    return ReadableScope(
        scope_node_id=scope_id,
        scope_level=str(level),
        visible_node_ids=visible,
        class_ids=tree.classes_under(subtree),
    )
