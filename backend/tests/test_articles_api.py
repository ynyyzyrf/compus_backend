"""HTTP-level checks for /articles and /admin/articles."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.content import Article, ArticleScope
from app.models.enums import ArticleStatus


@pytest.fixture()
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _make_article(db, **kw):
    a = Article(
        type=kw.get("type_", "announcement"),
        title=kw["title"],
        content=kw.get("content", "x"),
        summary=kw.get("summary"),
        cover_url=None,
        is_pinned=kw.get("is_pinned", False),
        status=kw.get("status", ArticleStatus.PUBLISHED),
        publish_at=kw.get("publish_at") or datetime.now(timezone.utc),
        created_by=kw.get("author_id"),
    )
    db.add(a)
    db.flush()
    for sid in kw.get("scope_ids", []) or []:
        db.add(ArticleScope(article_id=a.id, organization_id=sid))
    db.flush()
    return a


def test_list_requires_login(client):
    assert client.get("/api/v1/articles").status_code == 401


def test_user_sees_only_published(ctx, client):
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", ctx.org_by_name("XX校友組織", None).id).id)
    _make_article(ctx.db, title="open", scope_ids=[])
    _make_article(ctx.db, title="draft", scope_ids=[], status=ArticleStatus.DRAFT)
    _make_article(ctx.db, title="scoped", scope_ids=[dept_cs.id])

    resp = client.get("/api/v1/articles", headers=_auth(ctx.user("周可欣")))
    assert resp.status_code == 200
    titles = [a["title"] for a in resp.json()]
    assert titles == ["open"]


def test_user_get_scoped_article_is_404(ctx, client):
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", ctx.org_by_name("XX校友組織", None).id).id)
    a = _make_article(ctx.db, title="cs only", scope_ids=[dept_cs.id])

    assert client.get(
        f"/api/v1/articles/{a.id}", headers=_auth(ctx.user("周可欣"))
    ).status_code == 404
    assert client.get(
        f"/api/v1/articles/{a.id}", headers=_auth(ctx.user("張晨"))
    ).status_code == 200


def test_admin_crud(ctx, client):
    school = ctx.org_by_name("XX校友組織", None)
    dept_cs = ctx.org_by_name("計算機系", ctx.org_by_name("信息工程分院", school.id).id)

    headers = _auth(ctx.user("MAG"))

    create_payload = {
        "type": "news",
        "title": "校園更新",
        "content": "正文",
        "summary": "摘要",
        "is_pinned": True,
        "status": "published",
        "scope_ids": [dept_cs.id],
    }
    resp = client.post("/api/v1/admin/articles", json=create_payload, headers=headers)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["scope_ids"] == [dept_cs.id]
    aid = created["id"]

    # Update: change title + clear scope.
    resp = client.put(
        f"/api/v1/admin/articles/{aid}",
        json={"title": "校園更新 2", "scope_ids": []},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "校園更新 2"
    assert resp.json()["scope_ids"] == []

    # Delete
    assert client.delete(
        f"/api/v1/admin/articles/{aid}", headers=headers
    ).status_code == 204
    assert client.get(
        f"/api/v1/admin/articles/{aid}", headers=headers
    ).status_code == 404


def test_admin_endpoints_require_super_admin(ctx, client):
    assert client.get(
        "/api/v1/admin/articles", headers=_auth(ctx.user("張晨"))
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/articles",
        json={"type": "news", "title": "x"},
        headers=_auth(ctx.user("張晨")),
    ).status_code == 403
