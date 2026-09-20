"""Admin center: dashboard / members / organizations / permissions."""

from sqlalchemy import select

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.core.security import create_access_token
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
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_dashboard_returns_stats(ctx, client):
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(ctx.user("MAG")))
    assert resp.status_code == 200
    body = resp.json()
    assert body["member_total"] == 7
    assert body["active_member_total"] == 7
    assert body["college_count"] == 3
    assert body["department_count"] == 7
    assert body["class_count"] == 9


def test_dashboard_requires_super_admin(ctx, client):
    assert client.get(
        "/api/v1/admin/dashboard", headers=_auth(ctx.user("張晨"))
    ).status_code == 403


def test_members_list_and_filter(ctx, client):
    headers = _auth(ctx.user("MAG"))
    resp = client.get("/api/v1/admin/members", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 7
    assert any(m["name"] == "MAG" for m in body["items"])

    # search
    resp = client.get("/api/v1/admin/members?q=陳", headers=headers)
    assert all("陳" in m["name"] for m in resp.json()["items"])

    # college filter
    college = ctx.org_by_name("信息工程分院", ctx.org_by_name("XX校友組織", None).id)
    resp = client.get(
        f"/api/v1/admin/members?college_id={college.id}", headers=headers
    )
    names = {m["name"] for m in resp.json()["items"]}
    assert names == {"MAG", "張晨", "黃俊傑", "陳思遠"}


def test_member_update_and_disable(ctx, client):
    headers = _auth(ctx.user("MAG"))
    zhang = ctx.user("張晨")
    resp = client.put(
        f"/api/v1/admin/members/{zhang.id}",
        json={"phone": "13900000099", "position": "VP"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone"] == "13900000099"
    assert body["position"] == "VP"

    resp = client.post(
        f"/api/v1/admin/members/{zhang.id}/status",
        json={"status": "disabled"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


def test_organizations_crud(ctx, client):
    headers = _auth(ctx.user("MAG"))
    # list
    resp = client.get("/api/v1/admin/organizations", headers=headers)
    assert resp.status_code == 200
    initial = len(resp.json())
    assert initial == 20  # 1 school + 3 colleges + 7 departments + 9 classes

    # create department under 商學分院
    shang = ctx.org_by_name("商學分院", ctx.org_by_name("XX校友組織", None).id)
    resp = client.post(
        "/api/v1/admin/organizations",
        json={"name": "金融系", "type": "department", "parent_id": shang.id},
        headers=headers,
    )
    assert resp.status_code == 201
    new_id = resp.json()["id"]

    # update rename
    resp = client.put(
        f"/api/v1/admin/organizations/{new_id}",
        json={"name": "金融科技系"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "金融科技系"

    # try to set parent to self -> 400
    resp = client.put(
        f"/api/v1/admin/organizations/{new_id}",
        json={"parent_id": new_id},
        headers=headers,
    )
    assert resp.status_code == 400


def test_directory_permissions_round_trip(ctx, client):
    headers = _auth(ctx.user("MAG"))
    shang = ctx.org_by_name("商學分院", ctx.org_by_name("XX校友組織", None).id)
    yishu = ctx.org_by_name("藝術設計分院", ctx.org_by_name("XX校友組織", None).id)
    body = {
        "permissions": [
            {"organization_id": shang.id, "scope_type": "college", "is_enabled": True},
            {"organization_id": yishu.id, "scope_type": "college", "is_enabled": True},
        ]
    }
    resp = client.put("/api/v1/admin/directory-permissions", json=body, headers=headers)
    assert resp.status_code == 200
    enabled = {p["organization_name"]: p["is_enabled"] for p in resp.json()}
    assert enabled["商學分院"] is True
    assert enabled["藝術設計分院"] is True

    # 林嘉怡 now sees both colleges
    resp = client.get(
        "/api/v1/directory/tree",
        headers=_auth(ctx.user("林嘉怡")),
    )
    scope = resp.json()["scope_level"]
    assert scope == "college"


def test_admin_endpoints_reject_normal_user(ctx, client):
    headers = _auth(ctx.user("張晨"))
    for url in [
        "/api/v1/admin/dashboard",
        "/api/v1/admin/members",
        "/api/v1/admin/organizations",
        "/api/v1/admin/directory-permissions",
    ]:
        assert client.get(url, headers=headers).status_code == 403
