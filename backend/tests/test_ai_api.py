"""HTTP checks for the admin AI assistant boundary."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.activity import Activity, ActivityCheckin, ActivitySignup
from app.models.content import Article
from app.models.enums import ActivityStatus, ArticleStatus, ArticleType, SignupStatus
from app.models.relay import Relay, RelayResponse
from app.services import ai_tools


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


def _mk_activity(db, user_id: int):
    now = datetime.now(timezone.utc)
    row = Activity(
        title="2024全球校友創業論壇",
        cover_url="https://example.com/cover.jpg",
        description="創業交流與資源對接",
        location="清華大學 · 主樓廣場",
        organizer="校友商會",
        start_at=now + timedelta(days=3),
        end_at=now + timedelta(days=3, hours=3),
        signup_start_at=now - timedelta(days=1),
        signup_end_at=now + timedelta(days=1),
        status=ActivityStatus.SIGNING,
        created_by=user_id,
    )
    db.add(row)
    db.flush()
    return row


def test_ai_chat_rejects_non_admin(ctx, client):
    resp = client.post(
        "/api/v1/admin/ai/chat",
        json={"message": "統計活動"},
        headers=_auth(ctx.user("周可欣")),
    )
    assert resp.status_code == 403


def test_ai_chat_returns_clear_configuration_error_without_key(ctx, client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "openai_model", "gpt-test")

    resp = client.post(
        "/api/v1/admin/ai/chat",
        json={"message": "統計活動"},
        headers=_auth(ctx.user("MAG")),
    )
    assert resp.status_code == 503
    assert "OPENAI_API_KEY" in resp.json()["detail"]


def test_ai_tools_aggregate_platform_data(ctx):
    mag = ctx.user("MAG")
    user = ctx.user("周可欣")
    activity = _mk_activity(ctx.db, mag.id)
    signup = ActivitySignup(
        activity_id=activity.id,
        user_id=user.id,
        status=SignupStatus.SIGNED,
        phone="13900000001",
    )
    ctx.db.add(signup)
    ctx.db.flush()
    ctx.db.add(
        ActivityCheckin(activity_id=activity.id, user_id=user.id, signup_id=signup.id)
    )
    relay = Relay(title="校友商會年會參會接龍", status="open", created_by=mag.id)
    ctx.db.add(relay)
    ctx.db.flush()
    ctx.db.add(RelayResponse(relay_id=relay.id, user_id=user.id, response_json={}))
    ctx.db.add(
        Article(
            type=ArticleType.NEWS,
            title="校友新聞",
            content="正文",
            status=ArticleStatus.PUBLISHED,
            created_by=mag.id,
        )
    )
    ctx.db.flush()

    payload = ai_tools.build_tool_context(ctx.db, "創業論壇報名情況")
    tools = payload["tools"]

    assert tools["activity_stats"]["total"] == 1
    assert tools["signup_stats"]["total_signed"] == 1
    assert tools["checkin_stats"]["total_checked_in"] == 1
    assert tools["relay_stats"]["total_responses"] == 1
    assert tools["content_stats"]["published"] == 1
    assert tools["activity_summary"]["title"] == "2024全球校友創業論壇"


def test_ai_chat_uses_controlled_tool_context(ctx, client, monkeypatch):
    from app.core.config import settings
    from app.services import ai_service

    _mk_activity(ctx.db, ctx.user("MAG").id)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_model", "gpt-test")

    captured = {}

    def fake_call_llm(message, tool_context):
        captured["tool_context"] = tool_context
        return "共有 1 場活動。"

    monkeypatch.setattr(ai_service, "_call_llm", fake_call_llm)
    resp = client.post(
        "/api/v1/admin/ai/chat",
        json={"message": "請總結活動"},
        headers=_auth(ctx.user("MAG")),
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["answer"] == "共有 1 場活動。"
    assert captured["tool_context"]["tools"]["activity_stats"]["total"] == 1
