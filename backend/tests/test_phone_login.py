"""Verified phone identity and legacy account linking."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.deps import get_db
from app.main import app
from app.models.enums import Role, SignupStatus, Status
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
    monkeypatch.setattr(
        auth_service, "_code2session", lambda code: (f"openid-{code}", None)
    )
    monkeypatch.setattr(
        auth_service,
        "_get_phone",
        lambda code: (f"+86{code}", code),
    )


def test_unbound_wechat_login_requires_verified_phone(db, client, real_wechat):
    response = client.post("/api/v1/auth/wechat-login", json={"code": "new"})
    assert response.status_code == 428
    assert db.scalars(select(User).where(User.openid == "openid-new")).first() is None

    bound = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13900000001"},
    )
    assert bound.status_code == 200
    user_id = bound.json()["user"]["id"]
    assert bound.json()["user"]["verified_phone"] == "+8613900000001"
    assert db.get(User, user_id).phone_verified_at is not None

    repeat = client.post("/api/v1/auth/wechat-login", json={"code": "new"})
    assert repeat.status_code == 200
    assert repeat.json()["user"]["id"] == user_id


def test_verified_phone_links_legacy_account_and_moves_current_data(
    ctx, db, client, real_wechat
):
    from app.models.organization import Membership

    old = ctx.user("張晨")
    new = User(
        openid="openid-new", name="新用戶", role=Role.USER,
        status=Status.ACTIVE, phone="13900000002",
    )
    db.add(new)
    db.flush()
    class_id = ctx.class_id_for("周可欣")
    db.add(Membership(user_id=new.id, organization_id=class_id, is_primary=False))
    db.flush()
    new_id = new.id

    response = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000002"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] == old.id
    db.expire_all()
    assert db.get(User, new_id) is None
    assert db.get(User, old.id).openid == "openid-new"
    assert db.get(User, old.id).verified_phone == "+8613800000002"
    assert db.scalars(
        select(Membership).where(
            Membership.user_id == old.id,
            Membership.organization_id == class_id,
        )
    ).first() is not None


def test_admin_and_duplicate_legacy_phone_require_review(ctx, db, client, real_wechat):
    admin_phone = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000001"},
    )
    assert admin_phone.status_code == 409

    ctx.user("黃俊傑").phone = "13800000002"
    db.flush()
    duplicate = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000002"},
    )
    assert duplicate.status_code == 409


def test_manual_contact_phone_edit_does_not_change_verified_identity(
    ctx, db, client, real_wechat
):
    user = ctx.user("周可欣")
    user.verified_phone = "+8613800000006"
    db.flush()
    from app.core.security import create_access_token

    token = create_access_token(user.id, user.role)
    response = client.put(
        "/api/v1/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "13900000099"},
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "13900000099"
    assert response.json()["verified_phone"] == "+8613800000006"


def test_merge_preserves_checkin_when_both_accounts_signed_same_activity(
    ctx, db, client, real_wechat
):
    from app.models.activity import Activity, ActivityCheckin, ActivitySignup
    from app.models.organization import Membership

    old = ctx.user("張晨")
    source = User(
        openid="openid-new", name="新用戶", role=Role.USER, status=Status.ACTIVE
    )
    db.add(source)
    db.flush()
    old_class = ctx.class_id_for("張晨")
    db.add(Membership(user_id=source.id, organization_id=old_class))
    now = datetime.now(timezone.utc)
    activity = Activity(
        title="同場活動", location="校園", description="",
        start_at=now + timedelta(days=1), end_at=now + timedelta(days=1, hours=2),
        signup_start_at=now, signup_end_at=now + timedelta(hours=1),
        status="signing", created_by=source.id,
    )
    db.add(activity)
    db.flush()
    old_signup = ActivitySignup(
        activity_id=activity.id, user_id=old.id, status=SignupStatus.CANCELLED
    )
    new_signup = ActivitySignup(
        activity_id=activity.id, user_id=source.id, status=SignupStatus.SIGNED
    )
    db.add_all((old_signup, new_signup))
    db.flush()
    db.add(ActivityCheckin(
        activity_id=activity.id, user_id=source.id, signup_id=new_signup.id
    ))
    db.flush()

    response = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000002"},
    )
    assert response.status_code == 200
    db.expire_all()
    signups = list(db.scalars(
        select(ActivitySignup).where(ActivitySignup.activity_id == activity.id)
    ))
    checkins = list(db.scalars(
        select(ActivityCheckin).where(ActivityCheckin.activity_id == activity.id)
    ))
    assert [(row.user_id, row.id) for row in signups] == [(old.id, old_signup.id)]
    assert signups[0].status == SignupStatus.SIGNED
    assert [(row.user_id, row.signup_id) for row in checkins] == [(old.id, old_signup.id)]
    assert db.get(Activity, activity.id).created_by == old.id
    assert len(list(db.scalars(select(Membership).where(
        Membership.user_id == old.id,
        Membership.organization_id == old_class,
    )))) == 1


def test_wechat_phone_response_must_match_appid(monkeypatch):
    class Response:
        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

    monkeypatch.setattr(auth_service.settings, "wechat_appid", "wx-current")
    monkeypatch.setattr(auth_service, "_access_token", lambda: "stub-token")
    monkeypatch.setattr(
        auth_service.httpx,
        "post",
        lambda *args, **kwargs: Response({
            "errcode": 0,
            "phone_info": {
                "countryCode": "86",
                "purePhoneNumber": "13800000000",
                "watermark": {"appid": "wx-other"},
            },
        }),
    )
    with pytest.raises(auth_service.WeChatLoginError, match="資料無效"):
        auth_service._get_phone("one-use-phone-code")


def test_linking_phone_revokes_old_account_tokens(ctx, db, client, real_wechat):
    from app.core.security import create_access_token

    old = ctx.user("張晨")
    previous_token = create_access_token(old.id, old.role)
    linked = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000002"},
    )
    assert linked.status_code == 200
    assert linked.json()["user"]["id"] == old.id

    stale = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {previous_token}"},
    )
    assert stale.status_code == 401
    current = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {linked.json()['access_token']}"},
    )
    assert current.status_code == 200


def test_same_verified_phone_keeps_one_account_across_wechat_identities(
    db, client, real_wechat
):
    first = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "first", "phone_code": "13900000077"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "second", "phone_code": "13900000077"},
    )
    assert second.status_code == 200
    assert second.json()["user"]["id"] == first.json()["user"]["id"]
    assert len(list(db.scalars(
        select(User).where(User.verified_phone == "+8613900000077")
    ))) == 1
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {first.json()['access_token']}"},
    ).status_code == 401
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    ).status_code == 200


def test_contact_phone_cannot_claim_another_verified_identity(
    ctx, db, client, real_wechat
):
    old = ctx.user("張晨")
    old.verified_phone = "+8613900000088"
    db.flush()
    response = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000002"},
    )
    assert response.status_code == 409
    assert db.get(User, old.id).verified_phone == "+8613900000088"


def test_different_relay_answers_need_manual_review(ctx, db, client, real_wechat):
    from app.models.relay import Relay, RelayResponse

    old = ctx.user("張晨")
    source = User(openid="openid-new", name="新用戶", role=Role.USER, status=Status.ACTIVE)
    db.add(source)
    db.flush()
    relay = Relay(title="校友接力", created_by=old.id)
    db.add(relay)
    db.flush()
    db.add_all((
        RelayResponse(relay_id=relay.id, user_id=old.id, response_json={"answer": "甲"}),
        RelayResponse(relay_id=relay.id, user_id=source.id, response_json={"answer": "乙"}),
    ))
    db.flush()

    response = client.post(
        "/api/v1/auth/wechat-login",
        json={"code": "new", "phone_code": "13800000002"},
    )
    assert response.status_code == 409
    assert db.get(User, source.id) is not None
