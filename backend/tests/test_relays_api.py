"""HTTP-level checks for /relays and /admin/relays."""

from datetime import datetime, timedelta, timezone

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


def _relay_payload(**overrides):
    base = {
        "title": "国庆返校聚餐接龙",
        "description": "统计返校聚餐人数",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "status": "open",
        "fields": [
            {"label": "姓名", "field_type": "text", "required": True, "sort_order": 1},
            {
                "label": "是否参加",
                "field_type": "radio",
                "required": True,
                "options": ["参加", "不参加"],
                "sort_order": 2,
            },
            {"label": "同行人数", "field_type": "number", "required": False, "sort_order": 3},
        ],
    }
    base.update(overrides)
    return base


def test_admin_create_and_user_submit_relay(ctx, client):
    admin_headers = _auth(ctx.user("MAG"))
    create_resp = client.post(
        "/api/v1/admin/relays",
        json=_relay_payload(),
        headers=admin_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    relay_id = create_resp.json()["id"]

    user_headers = _auth(ctx.user("周可欣"))
    list_resp = client.get("/api/v1/relays", headers=user_headers)
    assert list_resp.status_code == 200
    assert [item["title"] for item in list_resp.json()] == ["国庆返校聚餐接龙"]

    detail_resp = client.get(f"/api/v1/relays/{relay_id}", headers=user_headers)
    assert detail_resp.status_code == 200
    assert [field["label"] for field in detail_resp.json()["fields"]] == ["姓名", "是否参加", "同行人数"]
    assert detail_resp.json()["my_response"] is None

    submit_resp = client.post(
        f"/api/v1/relays/{relay_id}/responses",
        json={"response": {"姓名": "周可欣", "是否参加": "参加", "同行人数": 2}},
        headers=user_headers,
    )
    assert submit_resp.status_code == 201, submit_resp.text
    assert submit_resp.json()["response"]["是否参加"] == "参加"

    duplicate_resp = client.post(
        f"/api/v1/relays/{relay_id}/responses",
        json={"response": {"姓名": "周可欣", "是否参加": "参加"}},
        headers=user_headers,
    )
    assert duplicate_resp.status_code == 409

    results_resp = client.get(
        f"/api/v1/admin/relays/{relay_id}/responses",
        headers=admin_headers,
    )
    assert results_resp.status_code == 200
    assert results_resp.json()["total"] == 1
    assert results_resp.json()["items"][0]["user_name"] == "周可欣"


def test_relay_required_fields_deadline_and_admin_auth(ctx, client):
    admin_headers = _auth(ctx.user("MAG"))
    create_resp = client.post(
        "/api/v1/admin/relays",
        json=_relay_payload(deadline=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()),
        headers=admin_headers,
    )
    relay_id = create_resp.json()["id"]

    user_headers = _auth(ctx.user("周可欣"))
    missing_required = client.post(
        f"/api/v1/relays/{relay_id}/responses",
        json={"response": {"姓名": "周可欣"}},
        headers=user_headers,
    )
    assert missing_required.status_code == 400

    assert client.post(
        "/api/v1/admin/relays",
        json=_relay_payload(title="普通用户不能创建"),
        headers=user_headers,
    ).status_code == 403

    closed_resp = client.post(
        "/api/v1/admin/relays",
        json=_relay_payload(
            title="已截止接龙",
            deadline=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        ),
        headers=admin_headers,
    )
    closed_id = closed_resp.json()["id"]
    late_resp = client.post(
        f"/api/v1/relays/{closed_id}/responses",
        json={"response": {"姓名": "周可欣", "是否参加": "参加"}},
        headers=user_headers,
    )
    assert late_resp.status_code == 400


def test_login_required_for_relays(client):
    assert client.get("/api/v1/relays").status_code == 401
