"""Real WeChat login uses only the AppID-scoped openid."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.deps import get_db
from app.main import app
from app.models.enums import Status
from app.models.user import User
from app.services import auth_service


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


@pytest.fixture()
def real_wechat(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "wechat_mock_login", False)
    monkeypatch.setattr(auth_service, "_code2session", lambda code: (f"openid-{code}", None))


def test_new_openid_creates_one_account_without_phone(db, client, real_wechat, monkeypatch):
    def fail_if_phone_called(*args, **kwargs):
        raise AssertionError("getPhoneNumber must not be called during login")

    monkeypatch.setattr(auth_service.httpx, "post", fail_if_phone_called)
    first = client.post("/api/v1/auth/wechat-login", json={"code": "new"})
    assert first.status_code == 200
    user_id = first.json()["user"]["id"]
    assert first.json()["access_token"]
    assert first.json()["user"]["openid"] == "openid-new"
    assert first.json()["user"]["verified_phone"] is None
    assert db.get(User, user_id).phone is None

    again = client.post("/api/v1/auth/wechat-login", json={"code": "new"})
    assert again.status_code == 200
    assert again.json()["user"]["id"] == user_id
    assert len(list(db.scalars(select(User).where(User.openid == "openid-new")))) == 1


def test_existing_openid_logs_in_without_verified_phone(ctx, db, client, real_wechat, monkeypatch):
    user = ctx.user("張晨")
    user.openid = "openid-existing"
    user.verified_phone = None
    db.flush()
    monkeypatch.setattr(auth_service, "_code2session", lambda code: ("openid-existing", None))

    response = client.post("/api/v1/auth/wechat-login", json={"code": "one-use-code"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] == user.id


def test_contact_phone_cannot_claim_another_openid(ctx, db, client, real_wechat):
    old = ctx.user("張晨")
    response = client.post("/api/v1/auth/wechat-login", json={"code": "different"})
    assert response.status_code == 200
    assert response.json()["user"]["id"] != old.id
    assert db.get(User, old.id).openid != "openid-different"


def test_disabled_openid_is_rejected(ctx, db, client, real_wechat, monkeypatch):
    user = ctx.user("張晨")
    user.openid = "openid-disabled"
    user.status = Status.DISABLED
    db.flush()
    monkeypatch.setattr(auth_service, "_code2session", lambda code: ("openid-disabled", None))

    response = client.post("/api/v1/auth/wechat-login", json={"code": "disabled"})
    assert response.status_code == 409


def test_code_exchange_uses_configured_appid_and_secret(monkeypatch):
    captured = {}

    class Response:
        def json(self):
            return {"openid": "current-app-openid", "unionid": "union"}

    def fake_get(url, *, params, timeout):
        captured.update(url=url, params=params, timeout=timeout)
        return Response()

    monkeypatch.setattr(auth_service.settings, "wechat_appid", "wx-current")
    monkeypatch.setattr(auth_service.settings, "wechat_secret", "test-secret")
    monkeypatch.setattr(auth_service.httpx, "get", fake_get)

    assert auth_service._code2session("login-code") == ("current-app-openid", "union")
    assert captured["url"] == auth_service.JSCODE2SESSION_URL
    assert captured["params"] == {
        "appid": "wx-current", "secret": "test-secret",
        "js_code": "login-code", "grant_type": "authorization_code",
    }
