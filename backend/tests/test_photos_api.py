"""HTTP checks for activity photos and admin review."""

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


def _mk_activity(db, **kw):
    now = datetime.now(timezone.utc)
    row = Activity(
        title=kw.get("title", "2024全球校友創業論壇"),
        cover_url=kw.get("cover_url", "https://example.com/cover.jpg"),
        description="d",
        location="清華大學 · 主樓廣場",
        organizer="校友商會",
        start_at=kw.get("start_at", now + timedelta(days=7)),
        end_at=kw.get("end_at", now + timedelta(days=7, hours=2)),
        signup_start_at=kw.get("signup_start_at", now - timedelta(days=1)),
        signup_end_at=kw.get("signup_end_at", now + timedelta(days=3)),
        status=kw.get("status", ActivityStatus.SIGNING),
        created_by=kw.get("created_by"),
    )
    db.add(row)
    db.flush()
    return row


def test_user_submission_is_pending_until_admin_approves(ctx, client):
    activity = _mk_activity(ctx.db)
    user_headers = _auth(ctx.user("周可欣"))

    created = client.post(
        f"/api/v1/activities/{activity.id}/photos",
        json={"file_url": "https://example.com/user-photo.jpg"},
        headers=user_headers,
    )
    assert created.status_code == 201, created.text
    photo = created.json()
    assert photo["status"] == "pending"
    assert photo["uploader_id"] == ctx.user("周可欣").id

    public_before = client.get(
        f"/api/v1/activities/{activity.id}/photos", headers=user_headers
    )
    assert public_before.status_code == 200
    assert public_before.json() == []

    admin_headers = _auth(ctx.user("MAG"))
    pending = client.get("/api/v1/admin/photos/pending", headers=admin_headers)
    assert pending.status_code == 200
    assert pending.json()["total"] == 1
    assert pending.json()["items"][0]["id"] == photo["id"]

    approved = client.post(
        f"/api/v1/admin/photos/{photo['id']}/approve", headers=admin_headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewed_at"] is not None

    public_after = client.get(
        f"/api/v1/activities/{activity.id}/photos", headers=user_headers
    )
    assert public_after.status_code == 200
    assert [p["file_url"] for p in public_after.json()] == [
        "https://example.com/user-photo.jpg"
    ]


def test_admin_submission_is_approved_immediately(ctx, client):
    activity = _mk_activity(ctx.db)
    headers = _auth(ctx.user("MAG"))

    resp = client.post(
        f"/api/v1/activities/{activity.id}/photos",
        json={"file_url": "https://example.com/admin-photo.jpg"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "approved"

    public_rows = client.get(
        f"/api/v1/activities/{activity.id}/photos", headers=headers
    ).json()
    assert len(public_rows) == 1


def test_user_can_list_own_uploads(ctx, client):
    activity = _mk_activity(ctx.db)
    headers = _auth(ctx.user("周可欣"))
    created = client.post(
        f"/api/v1/activities/{activity.id}/photos",
        json={"file_url": "https://example.com/mine.jpg"},
        headers=headers,
    ).json()

    resp = client.get("/api/v1/me/photos", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["id"] == created["id"]


def test_rejected_photo_stays_private_and_user_cannot_review(ctx, client):
    activity = _mk_activity(ctx.db)
    user_headers = _auth(ctx.user("周可欣"))
    photo_id = client.post(
        f"/api/v1/activities/{activity.id}/photos",
        json={"file_url": "https://example.com/rejected.jpg"},
        headers=user_headers,
    ).json()["id"]

    assert (
        client.get("/api/v1/admin/photos/pending", headers=user_headers).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/admin/photos/{photo_id}/approve", headers=user_headers
        ).status_code
        == 403
    )

    admin_headers = _auth(ctx.user("MAG"))
    rejected = client.post(
        f"/api/v1/admin/photos/{photo_id}/reject", headers=admin_headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    public_rows = client.get(
        f"/api/v1/activities/{activity.id}/photos", headers=user_headers
    ).json()
    assert public_rows == []
