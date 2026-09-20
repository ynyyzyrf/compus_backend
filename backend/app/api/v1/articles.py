from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.article import ArticleListItem, ArticleOut
from app.services import article_service

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=list[ArticleListItem])
def list_articles(
    current_user: CurrentUser,
    db: DbSession,
    type: str | None = Query(default=None, pattern="^(news|announcement|notice)$"),
    pinned_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[ArticleListItem]:
    items, _ = article_service.list_articles(
        db, current_user, type_=type, pinned_only=pinned_only, page=page, page_size=page_size
    )
    return [ArticleListItem.model_validate(a) for a in items]


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, current_user: CurrentUser, db: DbSession) -> ArticleOut:
    article = article_service.get_article(db, current_user, article_id)
    if article is None:
        # Don't reveal whether a draft exists outside the viewer's scope.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在或不在可見範圍"
        )
    return ArticleOut.model_validate(article)
