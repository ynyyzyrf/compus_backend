"""HTTP-level checks: auth required and scope enforced server-side."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app


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
