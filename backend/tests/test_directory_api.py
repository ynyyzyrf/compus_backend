"""HTTP-level checks: auth required and scope enforced server-side."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.organization import Organization


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
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


def test_tree_requires_login(client):
    assert client.get("/api/v1/directory/tree").status_code == 401


def test_tree_is_clipped_to_viewer_scope(client, ctx):
    resp = client.get(
        "/api/v1/directory/tree", headers=_auth(ctx.user("周可欣"))
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scope_level"] == "class"
    # school + 商學分院 + 市場營銷系 + her class
    assert len(data["nodes"]) == 4


def test_super_admin_tree_has_every_node(client, ctx):
    resp = client.get("/api/v1/directory/tree", headers=_auth(ctx.user("MAG")))
    nodes = resp.json()["nodes"]
    assert len(nodes) == 20  # 1 school + 3 colleges + 7 departments + 9 classes


def test_member_detail_cross_scope_is_404(client, ctx):
    # 周可欣 (商學) tries to read 張晨 (信息工程) -> hidden.
    resp = client.get(
        f"/api/v1/directory/members/{ctx.user('張晨').id}",
        headers=_auth(ctx.user("周可欣")),
    )
    assert resp.status_code == 404


def test_member_detail_in_scope_is_200(client, ctx):
    resp = client.get(
        f"/api/v1/directory/members/{ctx.user('黃俊傑').id}",
        headers=_auth(ctx.user("張晨")),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "黃俊傑"
    assert body["org_path"] == "信息工程分院 · 計算機系 · 2016級1班"


def test_directory_categories_use_own_profile_and_keep_visibility_scope(client, ctx):
    viewer = ctx.user("張晨")
    peer = ctx.user("黃俊傑")
    outside = ctx.user("林嘉怡")
    headers = _auth(viewer)
    url = "/api/v1/directory/members"
    viewer.city = None
    ctx.db.flush()
    missing = client.get(url, headers=headers, params={"category": "city"})
    assert missing.status_code == 409
    assert "所在城市" in missing.json()["detail"]

    response = client.put("/api/v1/me/profile", headers=headers, json={"city": " 深圳市 ", "profession": "软件开发"})
    assert response.status_code == 200
    assert response.json()["city"] == "深圳"
    for target in (peer, outside):
        target.city = "深圳"
        target.profession = " 软件开发 "
        target.details_visibility = "classmates"
    outside.alumni_discoverable = True
    ctx.db.flush()

    for category in ("city", "profession"):
        results = client.get(url, headers=headers, params={"category": category, "discover": True, "q": "级", "page_size": 1})
        assert results.status_code == 200
        assert results.json()["total"] == 1
        assert [item["id"] for item in results.json()["items"]] == [peer.id]
        assert "city" not in results.json()["items"][0]


def test_directory_relationships_use_viewers_class_and_year(client, ctx):
    viewer = ctx.user("張晨")
    peer = ctx.user("陳思遠")
    peer.alumni_discoverable = True
    ctx.db.get(Organization, ctx.class_id_for(viewer.name)).entry_year = 2016
    peer_class = ctx.db.get(Organization, ctx.class_id_for(peer.name))
    peer_class.entry_year = 2016
    ctx.db.flush()
    url = "/api/v1/directory/members"
    for relation, expected in {"class": False, "year": True, "department": False, "college": True}.items():
        result = client.get(url, headers=_auth(viewer), params={"discover": True, "relation": relation})
        assert result.status_code == 200
        assert (peer.id in {item["id"] for item in result.json()["items"]}) is expected
    assert client.put("/api/v1/me/profile", headers=_auth(peer), json={"basic_visibility": "private"}).status_code == 200
    assert client.get("/api/v1/connections/summary", headers=_auth(peer)).json()["discoverable"] is False
    result = client.get(url, headers=_auth(viewer), params={"discover": True, "relation": "year"})
    assert peer.id not in {item["id"] for item in result.json()["items"]}
