"""Article visibility + admin CRUD coverage."""

from datetime import datetime, timedelta, timezone

from app.api.v1 import articles as articles_module  # noqa: F401
from app.models.content import Article, ArticleScope
from app.models.enums import ArticleStatus
from app.services import article_service
from app.services.auth_service import create_access_token  # type: ignore


def _make_article(
    db,
    title: str,
    *,
    type_: str = "announcement",
    status: str = ArticleStatus.PUBLISHED,
    is_pinned: bool = False,
    scope_ids: list[int] | None = None,
    publish_at: datetime | None = None,
    author=None,
) -> Article:
    a = Article(
        type=type_,
        title=title,
        content=f"content of {title}",
        summary=title + " summary",
        cover_url=None,
        is_pinned=is_pinned,
        status=status,
        publish_at=publish_at or datetime.now(timezone.utc),
        created_by=author.id if author else None,
    )
    db.add(a)
    db.flush()
    for sid in scope_ids or []:
        db.add(ArticleScope(article_id=a.id, organization_id=sid))
    db.flush()
    return a


def test_published_visible_to_user_when_no_scopes(ctx):
    _make_article(ctx.db, "All visible", scope_ids=[])
    items, total = article_service.list_articles(ctx.db, ctx.user("周可欣"))
    assert total == 1
    assert items[0].title == "All visible"


def test_draft_never_visible_to_user(ctx):
    _make_article(ctx.db, "hidden draft", status=ArticleStatus.DRAFT, scope_ids=[])
    items, total = article_service.list_articles(ctx.db, ctx.user("周可欣"))
    assert total == 0


def test_scoped_article_visible_only_to_matching_members(ctx):
    # 信息工程分院 id; 計算機系 id
    college_ie = ctx.org_by_name("信息工程分院", ctx.org_by_name("XX校友組織", None).id)
    dept_cs = ctx.org_by_name("計算機系", college_ie.id)
    dept_other = ctx.org_by_name("市場營銷系", ctx.org_by_name("商學分院", ctx.org_by_name("XX校友組織", None).id).id)

    _make_article(ctx.db, "CS only", scope_ids=[dept_cs.id])
    _make_article(ctx.db, "CS dept + other dept", scope_ids=[dept_cs.id, dept_other.id])
    _make_article(ctx.db, "Other dept only", scope_ids=[dept_other.id])

    cs_member = ctx.user("張晨")  # 信息工程分院 計算機系 2016級1班
    items, _ = article_service.list_articles(ctx.db, cs_member)
    titles = {a.title for a in items}
    assert titles == {"CS only", "CS dept + other dept"}

    other = ctx.user("周可欣")  # 商學分院 市場營銷系 2019級1班
    items, _ = article_service.list_articles(ctx.db, other)
    titles = {a.title for a in items}
    assert titles == {"CS dept + other dept", "Other dept only"}


def test_pin_orders_pinned_first(ctx):
    _make_article(ctx.db, "A", is_pinned=False)
    _make_article(ctx.db, "B", is_pinned=True)
    items, _ = article_service.list_articles(ctx.db, ctx.user("周可欣"))
    assert [a.title for a in items] == ["B", "A"]


def test_super_admin_sees_every_published_article_regardless_of_scope(ctx):
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", ctx.org_by_name("XX校友組織", None).id).id)
    _make_article(ctx.db, "CS only", scope_ids=[dept_cs.id])
    _make_article(ctx.db, "open", scope_ids=[])
    items, _ = article_service.list_articles(ctx.db, ctx.user("MAG"))
    assert {a.title for a in items} == {"CS only", "open"}


def test_get_article_respects_scope(ctx):
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", ctx.org_by_name("XX校友組織", None).id).id)
    a = _make_article(ctx.db, "CS only", scope_ids=[dept_cs.id])

    assert article_service.get_article(ctx.db, ctx.user("張晨"), a.id) is not None
    assert article_service.get_article(ctx.db, ctx.user("周可欣"), a.id) is None


def test_create_and_update_article_replaces_scopes(ctx):
    from app.schemas.article import ArticleCreate, ArticleUpdate

    school = ctx.org_by_name("XX校友組織", None)
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", school.id).id)

    payload = ArticleCreate(
        type="announcement",
        title="About alumni",
        content="Hello",
        scope_ids=[dept_cs.id],
    )
    article = article_service.create_article(ctx.db, payload, ctx.user("MAG"))
    assert article.id is not None
    assert ctx.db.scalars(
        __import__("sqlalchemy").select(ArticleScope).where(ArticleScope.article_id == article.id)
    ).all() != []

    # Update without scope_ids leaves scopes unchanged.
    article_service.update_article(
        ctx.db,
        article.id,
        ArticleUpdate(title="Updated"),
    )
    assert ctx.db.get(Article, article.id).title == "Updated"

    # Update with scope_ids=[] clears scopes.
    article_service.update_article(
        ctx.db,
        article.id,
        ArticleUpdate(scope_ids=[]),
    )
    scopes = ctx.db.scalars(
        __import__("sqlalchemy").select(ArticleScope).where(ArticleScope.article_id == article.id)
    ).all()
    assert scopes == []


def test_delete_article_cascades_scopes(ctx):
    school = ctx.org_by_name("XX校友組織", None)
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", school.id).id)
    a = _make_article(ctx.db, "to delete", scope_ids=[dept_cs.id])
    assert article_service.delete_article(ctx.db, a.id)
    assert ctx.db.get(Article, a.id) is None
