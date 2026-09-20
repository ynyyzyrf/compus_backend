from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import DbSession, SuperAdmin
from app.schemas.article import (
    ArticleAdminOut,
    ArticleCreate,
    ArticleListPage,
    ArticleUpdate,
)
from app.services import article_service

router = APIRouter(prefix="/admin/articles", tags=["admin/articles"])


def _serialize(article, scope_ids: list[int]) -> ArticleAdminOut:
    return ArticleAdminOut(
        id=article.id,
        type=article.type,
        title=article.title,
        cover_url=article.cover_url,
        summary=article.summary,
        content=article.content,
        is_pinned=article.is_pinned,
        status=article.status,
        publish_at=article.publish_at,
        author_id=article.created_by,
        created_at=article.created_at,
        scope_ids=scope_ids,
    )


@router.get("", response_model=ArticleListPage)
def list_articles(
    _: SuperAdmin,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(draft|published|offline)$"),
    type: str | None = Query(default=None, pattern="^(news|announcement|notice)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ArticleListPage:
    items, total = article_service.list_admin_articles(
        db, page=page, page_size=page_size, status=status_filter, type_=type
    )
    rows = [
        _serialize(a, article_service._scope_ids_of(db, a.id))  # noqa: SLF001
        for a in items
    ]
    return ArticleListPage(items=rows, total=total, page=page, page_size=page_size)


@router.post("", response_model=ArticleAdminOut, status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleCreate, admin: SuperAdmin, db: DbSession) -> ArticleAdminOut:
    article = article_service.create_article(db, payload, admin)
    return _serialize(article, payload.scope_ids)


@router.get("/{article_id}", response_model=ArticleAdminOut)
def get_article(article_id: int, _: SuperAdmin, db: DbSession) -> ArticleAdminOut:
    article = article_service.get_admin_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")
    return _serialize(article, article_service._scope_ids_of(db, article_id))  # noqa: SLF001


@router.put("/{article_id}", response_model=ArticleAdminOut)
def update_article(
    article_id: int, payload: ArticleUpdate, _: SuperAdmin, db: DbSession
) -> ArticleAdminOut:
    article = article_service.update_article(db, article_id, payload)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")
    return _serialize(article, article_service._scope_ids_of(db, article_id))  # noqa: SLF001


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int, _: SuperAdmin, db: DbSession) -> None:
    if not article_service.delete_article(db, article_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")
