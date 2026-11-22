"""In-memory organization tree helpers.

Organization sizes (school -> colleges -> departments -> classes) are small
enough to load in one query, so traversal is done over a dict instead of
recursive SQL.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import OrgType, Status
from app.models.organization import Organization

CLASS_PATHS = (
    (OrgType.CLASS, OrgType.DEPARTMENT, OrgType.COLLEGE, OrgType.SCHOOL),
    (OrgType.CLASS, OrgType.MAJOR, OrgType.DEPARTMENT, OrgType.COLLEGE, OrgType.SCHOOL),
)


def normalize_org_keyword(value: str) -> str:
    compact = re.sub(r"(\d)\s+(?=[班级級])", r"\1", value.casefold())
    return re.sub(r"(\d)級", r"\1级", compact)


@dataclass
class OrgTree:
    nodes: dict[int, Organization]
    children: dict[int | None, list[int]]

    def ancestors(self, node_id: int) -> list[int]:
        """Return ids from ``node_id`` up to the root (node first, root last)."""
        chain: list[int] = []
        cur: int | None = node_id
        seen: set[int] = set()
        while cur is not None and cur in self.nodes and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = self.nodes[cur].parent_id
        return chain

    def descendants(self, node_id: int) -> set[int]:
        """Return ``node_id`` and all of its descendants."""
        result: set[int] = {node_id}
        stack = [node_id]
        while stack:
            current = stack.pop()
            for child in self.children.get(current, []):
                if child not in result:
                    result.add(child)
                    stack.append(child)
        return result

    def classes_under(self, node_ids: set[int]) -> set[int]:
        return {
            nid
            for nid in node_ids
            if self.school_for_class(nid) is not None
        }

    def school_for_class(self, class_id: int) -> int | None:
        chain = self.ancestors(class_id)
        if tuple(self.nodes[node].type for node in chain) not in CLASS_PATHS:
            return None
        school_id = chain[-1]
        return school_id if self.nodes[school_id].parent_id is None else None

    def label(self, node_id: int) -> str:
        node = self.nodes[node_id]
        if node.entry_year and f"{node.entry_year}级" not in node.name and f"{node.entry_year}級" not in node.name:
            return f"{node.entry_year}级 {node.name}"
        return node.name

    def path_name(self, node_id: int, sep: str = " · ") -> str:
        chain = self.ancestors(node_id)
        # ancestors() goes node -> root; reverse for root -> node, drop school.
        ordered = list(reversed(chain))
        names = [
            self.label(nid)
            for nid in ordered
            if self.nodes[nid].type != OrgType.SCHOOL
        ]
        return sep.join(names)

    def find_by_path_keyword(self, keyword: str) -> set[int]:
        """Return node ids whose own name or any ancestor name contains keyword."""
        term = normalize_org_keyword(keyword)
        number_term = re.compile(rf"(?<!\d){re.escape(term)}") if re.fullmatch(r"\d+(?:班|级)", term) else None
        hits: set[int] = set()
        for nid, node in self.nodes.items():
            chain_names = [normalize_org_keyword(self.label(a)) for a in self.ancestors(nid)]
            if any(number_term.search(name) if number_term else term in name for name in chain_names):
                hits.add(nid)
        return hits


def load_org_tree(db: Session, only_active: bool = True) -> OrgTree:
    stmt = select(Organization)
    if only_active:
        stmt = stmt.where(Organization.status == Status.ACTIVE)
    orgs = list(db.scalars(stmt.order_by(Organization.sort_order, Organization.id)))
    nodes = {o.id: o for o in orgs}
    children: dict[int | None, list[int]] = {}
    for o in orgs:
        children.setdefault(o.parent_id, []).append(o.id)
    return OrgTree(nodes=nodes, children=children)
