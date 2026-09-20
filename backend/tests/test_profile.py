"""Profile (self /me/profile) + extended member card tests."""

from datetime import date

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


def test_my_profile_returns_all_extended_fields(ctx, client):
    user = ctx.user("MAG")
    resp = client.get("/api/v1/me/profile", headers=_auth(user))
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "name",
        "name_en",
        "phone",
        "wechat_id",
        "email",
        "profession",
        "profession_en",
        "position",
        "company_name",
        "company_address",
        "company_founded_at",
        "bio",
        "business_description",
        "referrals_needed",
        "personal_experience",
        "resources_offered",
        "chamber_chapter",
        "chamber_member_no",
        "chamber_join_date",
        "chamber_score",
        "role",
        "status",
    ):
        assert key in body, f"missing key: {key}"


def test_my_profile_update_persists(ctx, client):
    headers = _auth(ctx.user("張晨"))
    payload = {
        "name_en": "Zhang Chen",
        "phone": "13900000001",
        "company_name": "跨易國際物流",
        "company_address": "廣州市天河區珠江新城",
        "company_founded_at": "2010-06-15",
        "profession": "國際物流",
        "profession_en": "International Logistics",
        "position": "創始人",
        "business_description": "全航線偏點運輸 / 跨境支付",
        "referrals_needed": "貿易商 / 華人 / 國外客戶",
        "personal_experience": "廣外財經國貿，20年國際物流從業",
        "resources_offered": "船東資源 / 2000+ 國外買家 / 100+ 海外代理",
        "chamber_chapter": "廣佛區",
        "chamber_member_no": "BNI-GF-001",
        "chamber_join_date": "2024-03-01",
        "chamber_score": 100,
    }
    resp = client.put("/api/v1/me/profile", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["company_name"] == "跨易國際物流"
    assert body["chamber_score"] == 100
    assert body["company_founded_at"] == "2010-06-15"

    # read-back verifies persistence
    resp2 = client.get("/api/v1/me/profile", headers=headers)
    assert resp2.json()["business_description"].startswith("全航線")


def test_my_profile_partial_update_only_touches_provided_fields(ctx, client):
    headers = _auth(ctx.user("周可欣"))
    full = client.get("/api/v1/me/profile", headers=headers).json()
    assert full["phone"]  # seeded with phone

    resp = client.put(
        "/api/v1/me/profile",
        json={"company_name": "新公司"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_name"] == "新公司"
    assert body["phone"] == full["phone"]  # unchanged


def test_my_profile_rejects_invalid_chamber_score(ctx, client):
    headers = _auth(ctx.user("周可欣"))
    resp = client.put(
        "/api/v1/me/profile", json={"chamber_score": -5}, headers=headers
    )
    assert resp.status_code == 422


def test_member_detail_now_returns_full_business_card(ctx, client):
    # 張晨 fills his profile, then 周可欣 (商學, can see via 通訊錄學院級可讀
    # is not enabled for 周可欣 — so use 周可欣 with phone query: 周可欣 can see
    # only own class. Use MAG as viewer to verify the new fields are serialized.
    zhang = ctx.user("張晨")
    client.put(
        "/api/v1/me/profile",
        json={"company_name": "跨易國際物流", "position": "創始人"},
        headers=_auth(zhang),
    )

    resp = client.get(
        f"/api/v1/directory/members/{zhang.id}",
        headers=_auth(ctx.user("林嘉怡")),  # 林嘉怡 = 商學, but college is closed
    )
    # 林嘉怡 cannot see 張晨 across colleges
    assert resp.status_code == 404

    resp = client.get(
        f"/api/v1/directory/members/{zhang.id}",
        headers=_auth(ctx.user("MAG")),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_name"] == "跨易國際物流"
    assert body["position"] == "創始人"
    assert body["profession"] is None  # untouched


def test_me_profile_requires_auth(client):
    assert client.get("/api/v1/me/profile").status_code == 401
