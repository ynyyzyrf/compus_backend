from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ===== user-facing =====


class ActivityListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    cover_url: str | None
    description: str
    location: str
    organizer: str | None
    start_at: datetime
    end_at: datetime
    signup_start_at: datetime
    signup_end_at: datetime
    capacity: int | None
    status: str  # signing / upcoming / ongoing / finished (computed)
    signup_count: int = 0
    checkin_count: int = 0


class ActivityDetail(ActivityListItem):
    created_by: int | None
    my_signed_up: bool = False
    my_checked_in: bool = False


# ===== signup =====


class SignupRequest(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=500)


class SignupResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    user_id: int
    phone: str | None
    remark: str | None
    status: str
    created_at: datetime


# ===== checkin =====


class CheckinRequest(BaseModel):
    """Token returned by ``POST /admin/activities/{id}/checkin-code``."""

    token: str = Field(min_length=1, max_length=4096)


class CheckinResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    user_id: int
    checkin_at: datetime
    checkin_method: str


class CheckinCodeOut(BaseModel):
    activity_id: int
    token: str
    expires_at: datetime


# ===== admin CRUD =====


class ActivityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    cover_url: str | None = None
    description: str = ""
    location: str = Field(min_length=1, max_length=200)
    organizer: str | None = None
    start_at: datetime
    end_at: datetime
    signup_start_at: datetime
    signup_end_at: datetime
    capacity: int | None = Field(default=None, ge=1, le=100000)
    status: str = Field(default="draft", pattern="^(draft|signing|upcoming|ongoing|finished)$")


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    cover_url: str | None = None
    description: str | None = None
    location: str | None = Field(default=None, min_length=1, max_length=200)
    organizer: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    signup_start_at: datetime | None = None
    signup_end_at: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=100000)
    status: str | None = Field(default=None, pattern="^(draft|signing|upcoming|ongoing|finished)$")


class ActivityAdminOut(ActivityListItem):
    description: str  # explicit (already in base, but admin returns full body)
    created_by: int | None


class ActivityAdminPage(BaseModel):
    items: list[ActivityAdminOut]
    total: int
    page: int
    page_size: int


class SignupRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str
    user_org_path: str
    phone: str | None
    remark: str | None
    status: str
    created_at: datetime
    checked_in: bool = False
    checkin_at: datetime | None = None


class SignupList(BaseModel):
    items: list[SignupRow]
    total: int
    signup_count: int
    checkin_count: int
    checkin_rate: float  # 0..1
    by_college: dict[str, int] = {}
