"""Production WeChat login behavior with the external code exchange stubbed."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.deps import get_db
from app.main import app
from app.services import auth_service


def test_new_wechat_openid_can_log_in_and_reuse_account(db, monkeypatch):
    monkeypatch.setattr(settings, "wechat_mock_login", False)
    monkeypatch.setattr(
        auth_service, "_code2session", lambda _code: ("new-miniapp-openid", None)
    )
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            first = client.post(
                "/api/v1/auth/wechat-login", json={"code": "stub-code"}
            )
            assert first.status_code == 200, first.text
            first_user = first.json()["user"]
            assert first_user["name"] == "未命名校友"
            assert first.json()["access_token"]

            second = client.post(
                "/api/v1/auth/wechat-login", json={"code": "another-stub-code"}
            )
            assert second.status_code == 200, second.text
            assert second.json()["user"]["id"] == first_user["id"]
    finally:
        app.dependency_overrides.clear()
