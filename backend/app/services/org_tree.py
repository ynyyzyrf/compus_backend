"""In-memory organization tree helpers.

Organization sizes (school -> colleges -> departments -> classes) are small
enough to load in one query, so traversal is done over a dict instead of
recursive SQL.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import OrgType, Status
from app.models.organization import Organization


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
            if nid in self.nodes and self.nodes[nid].type == OrgType.CLASS
        }

    def path_name(self, node_id: int, sep: str = " · ") -> str:
        chain = self.ancestors(node_id)
        # ancestors() goes node -> root; reverse for root -> node, drop school.
        ordered = list(reversed(chain))
        names = [
            self.nodes[nid].name
            for nid in ordered
            if self.nodes[nid].type != OrgType.SCHOOL
        ]
        return sep.join(names)

    def find_by_path_keyword(self, keyword: str) -> set[int]:
        """Return node ids whose own name or any ancestor name contains keyword."""
        hits: set[int] = set()
        for nid, node in self.nodes.items():
            chain_names = [self.nodes[a].name for a in self.ancestors(nid)]
            if any(keyword in name for name in chain_names):
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
