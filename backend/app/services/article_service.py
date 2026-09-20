"""Articles (news / announcements / notices) with org-scoped visibility.

User reads (PRD §15.3):
- only ``status=published``
- visible if the article has no scope rows OR if the viewer's primary class is
  inside any of the article's scope subtrees (inclusive of ancestors).

Admin writes (PRD §24.4): super admin only.
"""

from datetime import datetime

from sqlalchemy import desc, exists, or_, select
from sqlalchemy.orm import Session

from app.models.content import Article, ArticleScope
from app.models.enums import ArticleStatus, OrgType, Role
from app.models.organization import Membership
from app.models.user import User
from app.services.directory_permission import get_primary_class_id
from app.services.org_tree import load_org_tree

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

_no_scope_subq = ~select(ArticleScope.article_id).where(
    ArticleScope.article_id == Article.id
).exists()


def _user_visible_class_ids(db: Session, user: User) -> set[int]:
    """Return class ids the viewer is in (single primary class for V1)."""
    cid = get_primary_class_id(db, user.id)
    return {cid} if cid else set()


def _scoped_article_ids_visible_to(
    db: Session, viewer: User
) -> set[int] | None:
    """Return article ids with scope rows that the viewer may read.

    ``None`` means 'no scoped articles exist at all' (filter is a no-op).
    Empty set means 'scoped articles exist but none are visible to this viewer'.
    """
    if viewer.role == Role.SUPER_ADMIN:
        return None

    scoped_rows = list(db.scalars(select(ArticleScope)))
    if not scoped_rows:
        return None

    viewer_classes = _user_visible_class_ids(db, viewer)
    if not viewer_classes:
        return set()

    tree = load_org_tree(db)
    by_article: dict[int, list[int]] = {}
    for row in scoped_rows:
        by_article.setdefault(row.article_id, []).append(row.organization_id)

    allowed: set[int] = set()
    for article_id, org_ids in by_article.items():
        for org_id in org_ids:
            if org_id not in tree.nodes:
                continue
            target_classes = (
                {org_id}
                if tree.nodes[org_id].type == OrgType.CLASS
                else tree.classes_under(tree.descendants(org_id))
            )
            if target_classes & viewer_classes:
                allowed.add(article_id)
                break
    return allowed


def list_articles(
    db: Session,
    viewer: User,
    type_: str | None = None,
    pinned_only: bool = False,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Article], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    stmt = select(Article).where(Article.status == ArticleStatus.PUBLISHED)
    if type_:
        stmt = stmt.where(Article.type == type_)
    if pinned_only:
        stmt = stmt.where(Article.is_pinned.is_(True))

    scoped_allowed = _scoped_article_ids_visible_to(db, viewer)
    if scoped_allowed is not None:
        if not scoped_allowed:
            # No scoped article is visible -> only no-scope articles remain.
            stmt = stmt.where(_no_scope_subq)
        else:
            stmt = stmt.where(
                or_(_no_scope_subq, Article.id.in_(scoped_allowed))
            )

    total_stmt = select(Article).where(stmt.whereclause).order_by(None).with_only_columns(
        Article.id
    )
    total_count = len(db.execute(total_stmt).all())

    rows = db.execute(
        stmt.order_by(
            desc(Article.is_pinned),
            Article.publish_at.desc().nulls_last(),
            Article.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), total_count


def get_article(db: Session, viewer: User, article_id: int) -> Article | None:
    article = db.get(Article, article_id)
    if article is None or article.status != ArticleStatus.PUBLISHED:
        return None
    if viewer.role == Role.SUPER_ADMIN:
        return article

    scoped_rows = list(
        db.scalars(
            select(ArticleScope).where(ArticleScope.article_id == article_id)
        )
    )
    if not scoped_rows:
        return article  # no scope -> visible to everyone

    viewer_classes = _user_visible_class_ids(db, viewer)
    if not viewer_classes:
        return None

    tree = load_org_tree(db)
    for row in scoped_rows:
        if row.organization_id not in tree.nodes:
            continue
        target_classes = (
            {row.organization_id}
            if tree.nodes[row.organization_id].type == OrgType.CLASS
            else tree.classes_under(tree.descendants(row.organization_id))
        )
        if target_classes & viewer_classes:
            return article
    return None


# ===== admin writes =====


def _replace_scopes(db: Session, article_id: int, scope_ids: list[int]) -> None:
    db.execute(ArticleScope.__table__.delete().where(ArticleScope.article_id == article_id))
    for org_id in scope_ids:
        db.add(ArticleScope(article_id=article_id, organization_id=org_id))
    db.flush()


def _scope_ids_of(db: Session, article_id: int) -> list[int]:
    return list(
        db.scalars(
            select(ArticleScope.organization_id).where(ArticleScope.article_id == article_id)
        )
    )


def create_article(db: Session, payload, author: User) -> Article:
    article = Article(
        type=payload.type,
        title=payload.title,
        cover_url=payload.cover_url,
        summary=payload.summary,
        content=payload.content,
        is_pinned=payload.is_pinned,
        status=payload.status,
        publish_at=payload.publish_at,
        created_by=author.id,
    )
    db.add(article)
    db.flush()
    _replace_scopes(db, article.id, payload.scope_ids)
    db.commit()
    db.refresh(article)
    return article


def update_article(db: Session, article_id: int, payload) -> Article | None:
    article = db.get(Article, article_id)
    if article is None:
        return None

    data = payload.model_dump(exclude_unset=True)
    scope_ids = data.pop("scope_ids", None)

    for key, value in data.items():
        setattr(article, key, value)
    article.updated_at = datetime.utcnow()

    if scope_ids is not None:
        _replace_scopes(db, article.id, scope_ids)

    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article_id: int) -> bool:
    article = db.get(Article, article_id)
    if article is None:
        return False
    db.delete(article)
    db.commit()
    return True


def list_admin_articles(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: str | None = None,
    type_: str | None = None,
) -> tuple[list[Article], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    stmt = select(Article)
    if status:
        stmt = stmt.where(Article.status == status)
    if type_:
        stmt = stmt.where(Article.type == type_)

    # crude but exact; for our scale fine.
    count_stmt = select(Article).where(stmt.whereclause).order_by(None).with_only_columns(Article.id)
    total = len(db.execute(count_stmt).all())

    rows = db.execute(
        stmt.order_by(
            desc(Article.is_pinned),
            Article.updated_at.desc(),
            Article.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), total


def get_admin_article(db: Session, article_id: int) -> Article | None:
    article = db.get(Article, article_id)
    return article


def attach_scope_ids(article: Article, scope_ids: list[int]) -> dict:
    """Helper for admin responses: merge scope ids into a dict representation."""
    data = {
        "id": article.id,
        "type": article.type,
        "title": article.title,
        "cover_url": article.cover_url,
        "summary": article.summary,
        "content": article.content,
        "is_pinned": article.is_pinned,
        "status": article.status,
        "publish_at": article.publish_at,
        "created_by": article.created_by,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
        "scope_ids": scope_ids,
    }
    return data
