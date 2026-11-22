from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.session import get_db
from app.main import app
from app.models.connection import AlumniConnection
from app.models.organization import Organization
from app.models.user import User
from app.services import wechat_moderation

API = "/api/v1"


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def test_admin_adds_major_and_year_without_replacing_membership(db, ctx, client):
    admin = auth(ctx.user("MAG"))
    member = ctx.user("張晨")
    class_id = ctx.class_id_for("張晨")
    old_class = db.get(Organization, class_id)
    created = client.post(f"{API}/admin/organizations", headers=admin, json={
        "name": "软件工程", "type": "major", "parent_id": old_class.parent_id,
    })
    assert created.status_code == 201, created.text
    major_id = created.json()["id"]
    patch = {"parent_id": major_id, "entry_year": 2016}
    assert client.put(f"{API}/admin/organizations/{class_id}", headers=admin, json=patch).status_code == 200
    assert client.get(f"{API}/me/affiliation", headers=auth(member)).json()["class_id"] == class_id
    options = client.get(f"{API}/me/affiliation/options", headers=auth(member)).json()
    assert next(o for o in options if o["id"] == class_id)["entry_year"] == 2016

    payload = {"name": "2班", "type": "class", "parent_id": major_id, "entry_year": 2016}
    new_class = client.post(f"{API}/admin/organizations", headers=admin, json=payload)
    assert new_class.status_code == 201, new_class.text
    assert client.post(f"{API}/admin/organizations", headers=admin, json=payload).status_code == 400
    assert client.post(f"{API}/admin/organizations", headers=admin, json={
        **payload, "entry_year": 2017,
    }).status_code == 201

    unverified = User(openid="new-alumni-member", name="新校友")
    db.add(unverified)
    db.flush()
    new_class_id = new_class.json()["id"]
    assert client.post(f"{API}/me/affiliation/missing-class", headers=auth(unverified), json={
        "note": "软件工程 2016级 2班",
    }).status_code == 204
    assert client.get(f"{API}/admin/missing-classes", headers=auth(unverified)).status_code == 403
    assert client.get(f"{API}/admin/missing-classes", headers=admin).json()[0]["user_id"] == unverified.id
    applied = client.post(f"{API}/me/affiliation", headers=auth(unverified), json={"class_id": new_class_id})
    assert applied.status_code == 200, applied.text
    assert "软件工程 · 2016级 2班" in applied.json()["pending_org_path"]
    assert client.put(f"{API}/connections/preferences", headers=auth(unverified), json={"discoverable": True}).status_code == 403
    assert client.post(f"{API}/admin/affiliation-requests/{unverified.id}/approve", headers=admin).status_code == 200
    assert client.get(f"{API}/admin/missing-classes", headers=admin).json() == []


def test_cross_department_search_and_friendship_respect_explicit_sharing(db, ctx, client, monkeypatch):
    sender, target, duplicate = ctx.user("周可欣"), ctx.user("張晨"), ctx.user("黃俊傑")
    outsider = ctx.user("MAG")
    duplicate.name = target.name
    target.wechat_id = "private-wechat"
    target.phone = "private-phone"
    grade = db.get(Organization, ctx.class_id_for("張晨"))
    grade.entry_year = 2016
    db.flush()
    sender_auth, target_auth = auth(sender), auth(target)

    params = {"q": target.name, "entry_year": 2016, "class_id": grade.id, "discover": True}
    search = lambda: client.get(f"{API}/directory/members", headers=sender_auth, params=params)
    request_url = f"{API}/connections/{target.id}/request"
    assert search().json()["items"] == []
    assert client.post(request_url, headers=sender_auth, json={}).status_code == 404
    assert client.put(f"{API}/connections/preferences", headers=target_auth, json={"discoverable": True}).status_code == 200
    items = search().json()["items"]
    assert [row["id"] for row in items] == [target.id]
    assert not items[0]["can_view_profile"]
    assert "phone" not in items[0] and "wechat_id" not in items[0]
    assert client.get(f"{API}/directory/members/{target.id}", headers=sender_auth).status_code == 404
    assert client.get(f"{API}/directory/members", headers=sender_auth, params={
        **params, "entry_year": 2017,
    }).json()["total"] == 0
    assert client.get(f"{API}/directory/members", headers=sender_auth, params={
        **params, "discover": False,
    }).json()["total"] == 0

    checked = []
    monkeypatch.setattr(wechat_moderation, "check_alumni_message", lambda _, text: checked.append(text))
    msg = {"message": "你好，我也是本校校友"}
    assert client.post(request_url, headers=sender_auth, json=msg).status_code == 201
    assert client.post(request_url, headers=sender_auth, json=msg).status_code == 201
    assert checked == [msg["message"]]
    assert client.get(f"{API}/connections", headers=auth(outsider)).json() == []
    assert client.get(f"{API}/connections/summary", headers=target_auth).json()["unread"] == 1
    incoming = client.get(f"{API}/connections", headers=target_auth).json()
    assert incoming[0]["message"] == msg["message"]
    assert incoming[0]["incoming"] and incoming[0]["peer_wechat_id"] is None
    assert client.post(f"{API}/connections/read", headers=target_auth, json={
        "peer_ids": [sender.id],
    }).status_code == 204
    assert client.get(f"{API}/connections/summary", headers=target_auth).json()["unread"] == 0

    assert client.post(f"{API}/connections/{target.id}/respond", headers=sender_auth, json={"action": "accept"}).status_code == 404
    assert client.post(f"{API}/connections/{sender.id}/respond", headers=target_auth, json={"action": "accept"}).status_code == 200
    assert client.get(f"{API}/connections", headers=sender_auth).json()[0]["peer_wechat_id"] is None
    assert client.put(f"{API}/connections/{sender.id}/wechat", headers=target_auth, json={"share": True}).status_code == 200
    assert client.get(f"{API}/connections", headers=sender_auth).json()[0]["peer_wechat_id"] == "private-wechat"
    assert client.put(f"{API}/connections/{sender.id}/wechat", headers=target_auth, json={"share": False}).status_code == 200
    assert client.get(f"{API}/connections", headers=sender_auth).json()[0]["peer_wechat_id"] is None
    assert client.put(f"{API}/connections/preferences", headers=target_auth, json={"discoverable": False}).status_code == 200
    assert search().json()["items"] == []


def test_moderation_failure_does_not_create_request_and_decline_enforces_cooldown(db, ctx, client, monkeypatch):
    sender, target = ctx.user("張晨"), ctx.user("黃俊傑")
    url = f"{API}/connections/{target.id}/request"
    payload = {"message": "一起参加校友活动"}

    def reject_text(_openid, _message):
        raise HTTPException(422, "留言未通过审核")

    monkeypatch.setattr(wechat_moderation, "check_alumni_message", reject_text)
    assert client.post(url, headers=auth(sender), json=payload).status_code == 422
    assert client.get(f"{API}/connections", headers=auth(target)).json() == []
    monkeypatch.setattr(wechat_moderation, "check_alumni_message", lambda *_: None)
    assert client.post(url, headers=auth(sender), json=payload).status_code == 201
    assert client.post(f"{API}/connections/{sender.id}/respond", headers=auth(target), json={
        "action": "decline",
    }).status_code == 200
    assert client.post(url, headers=auth(sender), json=payload).status_code == 429
    row = db.get(AlumniConnection, tuple(sorted([sender.id, target.id])))
    row.responded_at = datetime.now(UTC) - timedelta(days=8)
    db.flush()
    assert client.post(url, headers=auth(sender), json=payload).status_code == 201
