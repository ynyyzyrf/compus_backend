"""A new account can see the selectable organization tree before joining."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.deps import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.enums import Role, Status
from app.models.user import User


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


def _auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_affiliation_options_available_before_membership(db, client):
    user = User(openid="new-user", name="新校友", role=Role.USER, status=Status.ACTIVE)
    db.add(user)
    db.flush()

    status = client.get("/api/v1/me/affiliation", headers=_auth(user))
    assert status.status_code == 200
    assert status.json() == {"class_id": None, "org_path": "", "pending_class_id": None, "pending_org_path": ""}

    options = client.get("/api/v1/me/affiliation/options", headers=_auth(user))
    assert options.status_code == 200
    nodes = options.json()
    assert len(nodes) == 20
    assert {node["type"] for node in nodes} == {
        "school", "college", "department", "class"
    }
    assert all(set(node) == {"id", "name", "type", "parent_id"} for node in nodes)


def test_existing_affiliation_is_read_from_primary_membership(ctx, client):
    user = ctx.user("張晨")
    response = client.get("/api/v1/me/affiliation", headers=_auth(user))
    assert response.status_code == 200
    assert response.json() == {
        "class_id": ctx.class_id_for("張晨"),
        "org_path": "信息工程分院 · 計算機系 · 2016級1班",
        "pending_class_id": None,
        "pending_org_path": "",
    }


def test_affiliation_options_require_login(client):
    assert client.get("/api/v1/me/affiliation/options").status_code == 401


def test_affiliation_requires_review_before_directory_access(db, client, ctx):
    from app.models.organization import Membership

    user = User(openid="onboarding-user", name="待審校友", role=Role.USER, status=Status.ACTIVE)
    db.add(user)
    db.flush()
    class_id = ctx.class_id_for("張晨")
    assert client.post("/api/v1/me/affiliation", headers=_auth(user), json={"class_id": class_id, "name": "  王小明  "}).status_code == 200
    assert client.get("/api/v1/me/profile", headers=_auth(user)).json()["name"] == "王小明"
    assert client.get("/api/v1/me/affiliation", headers=_auth(user)).json()["pending_class_id"] == class_id
    assert db.scalars(select(Membership).where(Membership.user_id == user.id)).first() is None
    tree_before = client.get("/api/v1/directory/tree", headers=_auth(user)).json()
    assert tree_before["nodes"] == []
    assert client.get(f"/api/v1/directory/members/{ctx.user('張晨').id}", headers=_auth(user)).status_code == 404
    assert client.post("/api/v1/me/affiliation", headers=_auth(user), json={"class_id": class_id}).status_code == 200

    admin = db.scalars(select(User).where(User.role == Role.SUPER_ADMIN)).first()
    requests = client.get("/api/v1/admin/affiliation-requests", headers=_auth(admin))
    assert requests.status_code == 200
    assert any(row["user_id"] == user.id and row["name"] == "王小明" for row in requests.json())
    assert client.get("/api/v1/admin/affiliation-requests", headers=_auth(user)).status_code == 403
    assert client.post(f"/api/v1/admin/affiliation-requests/{user.id}/approve", headers=_auth(user)).status_code == 403
    approved = client.post(f"/api/v1/admin/affiliation-requests/{user.id}/approve", headers=_auth(admin))
    assert approved.status_code == 200
    affiliation = client.get("/api/v1/me/affiliation", headers=_auth(user)).json()
    assert affiliation["class_id"] == class_id
    assert affiliation["pending_class_id"] is None
    assert db.scalars(select(Membership).where(Membership.user_id == user.id, Membership.is_primary.is_(True))).one().organization_id == class_id
    assert client.get("/api/v1/directory/tree", headers=_auth(user)).json()["nodes"]


def test_invalid_class_and_reject(db, client, ctx):
    user = User(openid="reject-user", name="退回校友", role=Role.USER, status=Status.ACTIVE)
    db.add(user)
    db.flush()
    nodes = client.get("/api/v1/me/affiliation/options", headers=_auth(user)).json()
    school_id = next(n["id"] for n in nodes if n["type"] == "school")
    assert client.post("/api/v1/me/affiliation", headers=_auth(user), json={"class_id": school_id, "name": "  "}).status_code == 422
    assert client.post("/api/v1/me/affiliation", headers=_auth(user), json={"class_id": school_id}).status_code == 400
    class_id = ctx.class_id_for("張晨")
    assert client.post("/api/v1/me/affiliation", headers=_auth(user), json={"class_id": class_id}).status_code == 200
    admin = db.scalars(select(User).where(User.role == Role.SUPER_ADMIN)).first()
    assert client.post(f"/api/v1/admin/affiliation-requests/{user.id}/reject", headers=_auth(admin)).status_code == 200
    assert client.get("/api/v1/me/affiliation", headers=_auth(user)).json()["pending_class_id"] is None
