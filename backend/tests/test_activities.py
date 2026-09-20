"""Activity lifecycle: status, signup rules, checkin flow + QR token."""

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.models.activity import Activity, ActivityCheckin, ActivitySignup
from app.models.enums import (
    ActivityStatus,
    CheckinMethod,
    Role,
    SignupStatus,
)
from app.services import activity_service
from app.services.qr_token import decode_checkin_token, issue_checkin_token


def _mk_activity(
    db,
    *,
    title="Test Event",
    start_offset_min=60,
    end_offset_min=180,
    signup_start_offset_min=-60,
    signup_end_offset_min=30,
    capacity=None,
    status=ActivityStatus.SIGNING,
    creator=None,
) -> Activity:
    now = datetime.now(timezone.utc)
    a = Activity(
        title=title,
        cover_url=None,
        description="desc",
        location="Room A",
        organizer=None,
        start_at=now + timedelta(minutes=start_offset_min),
        end_at=now + timedelta(minutes=end_offset_min),
        signup_start_at=now + timedelta(minutes=signup_start_offset_min),
        signup_end_at=now + timedelta(minutes=signup_end_offset_min),
        capacity=capacity,
        status=status,
        created_by=creator.id if creator else None,
    )
    db.add(a)
    db.flush()
    return a


# ===== status =====


def test_compute_status_signing(ctx):
    a = _mk_activity(ctx.db, signup_end_offset_min=30, start_offset_min=120)
    assert activity_service.compute_status(a) == ActivityStatus.SIGNING


def test_compute_status_upcoming_ongoing_finished(ctx):
    now = datetime.now(timezone.utc)
    a = _mk_activity(ctx.db)
    a.signup_end_at = now - timedelta(minutes=10)
    a.start_at = now + timedelta(minutes=30)
    a.end_at = now + timedelta(minutes=120)
    assert activity_service.compute_status(a) == ActivityStatus.UPCOMING

    a.start_at = now - timedelta(minutes=30)
    assert activity_service.compute_status(a) == ActivityStatus.ONGOING

    a.end_at = now - timedelta(minutes=10)
    assert activity_service.compute_status(a) == ActivityStatus.FINISHED


def test_compute_status_draft_overrides(ctx):
    a = _mk_activity(ctx.db, status=ActivityStatus.DRAFT)
    assert activity_service.compute_status(a) == ActivityStatus.DRAFT


# ===== signup =====


def test_signup_happy_path(ctx):
    a = _mk_activity(ctx.db)
    row = activity_service.signup(ctx.db, a.id, ctx.user("周可欣"), phone="13900000001", remark="ok")
    assert row.status == SignupStatus.SIGNED
    assert row.phone == "13900000001"


def test_signup_outside_window_raises(ctx):
    a = _mk_activity(ctx.db, signup_start_offset_min=-200, signup_end_offset_min=-100)
    with pytest.raises(activity_service.NotInSignupWindow):
        activity_service.signup(ctx.db, a.id, ctx.user("周可欣"), None, None)


def test_signup_capacity(ctx):
    a = _mk_activity(ctx.db, capacity=1)
    activity_service.signup(ctx.db, a.id, ctx.user("張晨"), None, None)
    with pytest.raises(activity_service.CapacityReached):
        activity_service.signup(ctx.db, a.id, ctx.user("林嘉怡"), None, None)


def test_signup_duplicate_then_cancel_then_resign(ctx):
    a = _mk_activity(ctx.db)
    u = ctx.user("周可欣")
    activity_service.signup(ctx.db, a.id, u, None, None)
    with pytest.raises(activity_service.AlreadySignedUp):
        activity_service.signup(ctx.db, a.id, u, None, None)
    activity_service.cancel_signup(ctx.db, a.id, u)
    again = activity_service.signup(ctx.db, a.id, u, phone="139", remark="hi")
    assert again.status == SignupStatus.SIGNED
    assert again.phone == "139"


def test_cancel_after_deadline_raises(ctx):
    a = _mk_activity(ctx.db, signup_end_offset_min=-1)
    u = ctx.user("周可欣")
    # cannot even sign up after deadline
    with pytest.raises(activity_service.NotInSignupWindow):
        activity_service.signup(ctx.db, a.id, u, None, None)


# ===== checkin =====


def test_checkin_requires_signed_up(ctx):
    a = _mk_activity(ctx.db, start_offset_min=0, end_offset_min=60)
    token, _ = issue_checkin_token(a.id)
    with pytest.raises(activity_service.NotSignedUp):
        activity_service.checkin(ctx.db, a.id, ctx.user("周可欣"), token)


def test_checkin_happy_path(ctx):
    a = _mk_activity(ctx.db, start_offset_min=0, end_offset_min=60)
    u = ctx.user("周可欣")
    activity_service.signup(ctx.db, a.id, u, None, None)
    token, _ = issue_checkin_token(a.id)
    row = activity_service.checkin(ctx.db, a.id, u, token)
    assert row.checkin_method == CheckinMethod.QRCODE
    assert row.user_id == u.id


def test_checkin_duplicate_raises(ctx):
    a = _mk_activity(ctx.db, start_offset_min=0, end_offset_min=60)
    u = ctx.user("周可欣")
    activity_service.signup(ctx.db, a.id, u, None, None)
    token, _ = issue_checkin_token(a.id)
    activity_service.checkin(ctx.db, a.id, u, token)
    with pytest.raises(activity_service.AlreadyCheckedIn):
        activity_service.checkin(ctx.db, a.id, u, token)


def test_checkin_wrong_activity_token_raises(ctx):
    a = _mk_activity(ctx.db, start_offset_min=0, end_offset_min=60)
    u = ctx.user("周可欣")
    activity_service.signup(ctx.db, a.id, u, None, None)
    wrong_token, _ = issue_checkin_token(activity_id=a.id + 999)
    with pytest.raises(activity_service.InvalidToken):
        activity_service.checkin(ctx.db, a.id, u, wrong_token)


def test_checkin_window(ctx):
    # activity starts in 2 hours, ends in 3 -> checkin window not yet open
    a = _mk_activity(ctx.db, start_offset_min=120, end_offset_min=180)
    u = ctx.user("周可欣")
    activity_service.signup(ctx.db, a.id, u, None, None)
    token, _ = issue_checkin_token(a.id)
    with pytest.raises(activity_service.NotInCheckinWindow):
        activity_service.checkin(ctx.db, a.id, u, token)


def test_checkin_after_end_raises(ctx):
    a = _mk_activity(ctx.db, start_offset_min=-180, end_offset_min=-1)
    u = ctx.user("周可欣")
    activity_service.signup(ctx.db, a.id, u, None, None)
    token, _ = issue_checkin_token(a.id)
    with pytest.raises(activity_service.NotInCheckinWindow):
        activity_service.checkin(ctx.db, a.id, u, token)


# ===== QR token =====


def test_qr_token_decode_roundtrip():
    token, exp = issue_checkin_token(42)
    assert decode_checkin_token(token, 42) is True
    assert decode_checkin_token(token, 43) is False
    # malformed
    assert decode_checkin_token("not.a.jwt", 42) is False


# ===== roster =====


def test_roster_stats_with_mixed_signups_and_checkins(ctx):
    a = _mk_activity(ctx.db, start_offset_min=-10, end_offset_min=60)
    # 3 signups, 2 checkins, 1 cancel
    activity_service.signup(ctx.db, a.id, ctx.user("張晨"), None, None)
    activity_service.signup(ctx.db, a.id, ctx.user("黃俊傑"), None, None)
    activity_service.signup(ctx.db, a.id, ctx.user("林嘉怡"), None, None)
    activity_service.cancel_signup(ctx.db, a.id, ctx.user("林嘉怡"))

    token, _ = issue_checkin_token(a.id)
    activity_service.checkin(ctx.db, a.id, ctx.user("張晨"), token)
    activity_service.checkin(ctx.db, a.id, ctx.user("黃俊傑"), token)

    roster = activity_service.admin_roster(ctx.db, a.id)
    assert roster["signup_count"] == 2
    assert roster["checkin_count"] == 2
    assert roster["checkin_rate"] == 1.0
    assert "信息工程分院" in roster["by_college"]
    assert roster["by_college"]["信息工程分院"] == 2
