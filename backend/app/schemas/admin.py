from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# ===== dashboard =====


class DashboardStats(BaseModel):
    member_total: int
    active_member_total: int
    college_count: int
    department_count: int
    class_count: int
    signing_activity_total: int
    ongoing_activity_total: int
    recent_checkin_rate: float  # 0..1, last 3 finished activities


# ===== member admin =====


class MemberAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None
    role: str
    status: str
    openid: str | None
    unionid: str | None
    phone: str | None
    wechat_id: str | None
    email: str | None
    name_en: str | None
    profession: str | None
    profession_en: str | None
    position: str | None
    company_name: str | None
    company_address: str | None
    company_founded_at: date | None
    bio: str | None
    business_description: str | None
    referrals_needed: str | None
    personal_experience: str | None
    resources_offered: str | None
    chamber_chapter: str | None
    chamber_member_no: str | None
    chamber_join_date: date | None
    chamber_score: int | None
    primary_class_id: int | None
    primary_class_name: str | None
    primary_org_path: str


class MemberListPage(BaseModel):
    items: list[MemberAdminOut]
    total: int
    page: int
    page_size: int


class MemberUpdate(BaseModel):
    """Admin can edit every field except openid/unionid/role."""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    status: str | None = Field(default=None, pattern="^(active|disabled)$")
    role: str | None = Field(default=None, pattern="^(user|super_admin)$")

    phone: str | None = Field(default=None, max_length=32)
    wechat_id: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=128)
    name_en: str | None = Field(default=None, max_length=100)
    profession: str | None = Field(default=None, max_length=128)
    profession_en: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=200)
    company_address: str | None = Field(default=None, max_length=500)
    company_founded_at: date | None = None
    bio: str | None = None
    business_description: str | None = None
    referrals_needed: str | None = None
    personal_experience: str | None = None
    resources_offered: str | None = None
    chamber_chapter: str | None = Field(default=None, max_length=128)
    chamber_member_no: str | None = Field(default=None, max_length=64)
    chamber_join_date: date | None = None
    chamber_score: int | None = Field(default=None, ge=0, le=10000)


# ===== organization admin =====


class OrgNodeAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    parent_id: int | None
    sort_order: int
    status: str
    member_count: int = 0


class OrgNodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: str = Field(pattern="^(school|college|department|class)$")
    parent_id: int | None = None
    sort_order: int = 0


class OrgNodeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    parent_id: int | None = None
    sort_order: int | None = None
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


# ===== directory permissions =====


class DirectoryPermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: int
    organization_name: str
    organization_type: str
    scope_type: str  # class / department / college
    is_enabled: bool


class DirectoryPermissionItem(BaseModel):
    organization_id: int
    scope_type: str = Field(pattern="^(class|department|college)$")
    is_enabled: bool


class DirectoryPermissionBatchUpdate(BaseModel):
    permissions: list[DirectoryPermissionItem]
