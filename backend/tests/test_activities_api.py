"""HTTP-level checks for /activities and /admin/activities."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.activity import Activity
from app.models.enums import ActivityStatus


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


def _mk(db, **kw):
    now = datetime.now(timezone.utc)
    a = Activity(
        title=kw.get("title", "T"),
        description="d",
        location="loc",
        start_at=kw.get("start_at", now + timedelta(minutes=60)),
        end_at=kw.get("end_at", now + timedelta(minutes=180)),
        signup_start_at=kw.get("signup_start_at", now - timedelta(minutes=10)),
        signup_end_at=kw.get("signup_end_at", now + timedelta(minutes=30)),
        capacity=kw.get("capacity"),
        status=kw.get("status", ActivityStatus.SIGNING),
        created_by=kw.get("creator_id"),
    )
    db.add(a)
    db.flush()
    return a


def test_user_list_excludes_drafts(ctx, client):
    _mk(ctx.db, title="public", status=ActivityStatus.SIGNING)
    _mk(ctx.db, title="hidden", status=ActivityStatus.DRAFT)

    resp = client.get("/api/v1/activities", headers=_auth(ctx.user("周可欣")))
    assert resp.status_code == 200
    titles = [a["title"] for a in resp.json()]
    assert "public" in titles
    assert "hidden" not in titles


def test_user_can_signup_and_cancel(ctx, client):
    a = _mk(ctx.db, capacity=10)
    headers = _auth(ctx.user("周可欣"))
    resp = client.post(
        f"/api/v1/activities/{a.id}/signup",
        json={"phone": "13900000001", "remark": "first"},
        headers=headers,
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # duplicate
    resp = client.post(
        f"/api/v1/activities/{a.id}/signup", json={}, headers=headers
    )
    assert resp.status_code == 409

    # cancel
    resp = client.delete(f"/api/v1/activities/{a.id}/signup", headers=headers)
    assert resp.status_code == 204


def test_user_checkin_via_token(ctx, client):
    a = _mk(
        ctx.db,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    headers = _auth(ctx.user("周可欣"))
    # signup first
    assert client.post(
        f"/api/v1/activities/{a.id}/signup", json={}, headers=headers
    ).status_code == 201

    # admin issues token
    admin_headers = _auth(ctx.user("MAG"))
    code = client.post(
        f"/api/v1/admin/activities/{a.id}/checkin-code", headers=admin_headers
    ).json()
    token = code["token"]

    resp = client.post(
        f"/api/v1/activities/{a.id}/checkin",
        json={"token": token},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["checkin_method"] == "qrcode"

    # duplicate
    resp = client.post(
        f"/api/v1/activities/{a.id}/checkin",
        json={"token": token},
        headers=headers,
    )
    assert resp.status_code == 409


def test_user_checkin_without_signup_403(ctx, client):
    a = _mk(
        ctx.db,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    admin_headers = _auth(ctx.user("MAG"))
    token = client.post(
        f"/api/v1/admin/activities/{a.id}/checkin-code", headers=admin_headers
    ).json()["token"]

    resp = client.post(
        f"/api/v1/activities/{a.id}/checkin",
        json={"token": token},
        headers=_auth(ctx.user("周可欣")),
    )
    assert resp.status_code == 403


def test_user_checkin_with_invalid_token_400(ctx, client):
    a = _mk(
        ctx.db,
        start_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    headers = _auth(ctx.user("周可欣"))
    client.post(f"/api/v1/activities/{a.id}/signup", json={}, headers=headers)

    resp = client.post(
        f"/api/v1/activities/{a.id}/checkin",
        json={"token": "garbage.token.value"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_admin_only_endpoints_reject_user(ctx, client):
    a = _mk(ctx.db)
    headers = _auth(ctx.user("周可欣"))
    assert client.post("/api/v1/admin/activities", json={
        "title": "x", "location": "y",
        "start_at": "2030-01-01T00:00:00Z",
        "end_at": "2030-01-01T02:00:00Z",
        "signup_start_at": "2029-12-25T00:00:00Z",
        "signup_end_at": "2029-12-30T00:00:00Z",
    }, headers=headers).status_code == 403
    assert client.get(
        f"/api/v1/admin/activities/{a.id}/signups", headers=headers
    ).status_code == 403


def test_admin_create_and_roster(ctx, client):
    payload = {
        "title": "T",
        "location": "Room",
        "description": "x",
        "start_at": "2030-01-01T00:00:00Z",
        "end_at": "2030-01-01T02:00:00Z",
        "signup_start_at": "2029-12-25T00:00:00Z",
        "signup_end_at": "2029-12-30T00:00:00Z",
        "capacity": 5,
        "status": "signing",
    }
    resp = client.post(
        "/api/v1/admin/activities",
        json=payload,
        headers=_auth(ctx.user("MAG")),
    )
    assert resp.status_code == 201, resp.text
    aid = resp.json()["id"]

    roster = client.get(
        f"/api/v1/admin/activities/{aid}/signups",
        headers=_auth(ctx.user("MAG")),
    ).json()
    assert roster["total"] == 0
    assert roster["checkin_rate"] == 0.0


def test_login_required(client):
    assert client.get("/api/v1/activities").status_code == 401
