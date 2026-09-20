from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArticleOut(BaseModel):
    """User-facing article payload (only published items)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    cover_url: str | None = None
    summary: str | None = None
    content: str
    is_pinned: bool
    publish_at: datetime | None = None
    author_id: int | None = None
    created_at: datetime


class ArticleListItem(BaseModel):
    """List rows skip heavy content for performance."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    cover_url: str | None = None
    summary: str | None = None
    is_pinned: bool
    publish_at: datetime | None = None
    created_at: datetime


# ===== admin CRUD =====


class ArticleScopeIn(BaseModel):
    organization_id: int


class ArticleCreate(BaseModel):
    type: str = Field(pattern="^(news|announcement|notice)$")
    title: str = Field(min_length=1, max_length=200)
    cover_url: str | None = None
    summary: str | None = None
    content: str = ""
    is_pinned: bool = False
    status: str = Field(default="draft", pattern="^(draft|published|offline)$")
    publish_at: datetime | None = None
    scope_ids: list[int] = []  # empty => visible to all members


class ArticleUpdate(BaseModel):
    type: str | None = Field(default=None, pattern="^(news|announcement|notice)$")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    cover_url: str | None = None
    summary: str | None = None
    content: str | None = None
    is_pinned: bool | None = None
    status: str | None = Field(default=None, pattern="^(draft|published|offline)$")
    publish_at: datetime | None = None
    scope_ids: list[int] | None = None


class ArticleAdminOut(ArticleOut):
    """Adds status + scope ids for the management UI."""

    status: str
    scope_ids: list[int] = []


class ArticleListPage(BaseModel):
    items: list[ArticleAdminOut]
    total: int
    page: int
    page_size: int
