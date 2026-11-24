from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.services.name_display import display_name_en

ProfileVisibility = Literal["private", "friends", "classmates"]


class MyProfile(BaseModel):
    """Full profile payload for the current user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_en: str | None = None
    avatar_url: str | None = None

    @computed_field
    @property
    def name_en_display(self) -> str | None:
        return display_name_en(self.name, self.name_en)

    # contact
    phone: str | None = None
    verified_phone: str | None = None
    wechat_id: str | None = None
    email: str | None = None
    city: str | None = None
    basic_visibility: ProfileVisibility = "classmates"
    contact_visibility: ProfileVisibility = "private"
    details_visibility: ProfileVisibility = "private"

    # profession / position / company
    profession: str | None = None
    profession_en: str | None = None
    position: str | None = None
    company_name: str | None = None
    company_address: str | None = None
    company_founded_at: date | None = None

    # business narrative
    bio: str | None = None
    business_description: str | None = None
    referrals_needed: str | None = None
    personal_experience: str | None = None
    resources_offered: str | None = None

    # chamber / 商會
    chamber_chapter: str | None = None
    chamber_member_no: str | None = None
    chamber_join_date: date | None = None
    chamber_score: int | None = None

    # access
    role: str
    status: str


class MyProfileUpdate(BaseModel):
    """Editable subset of the current user's profile."""

    name: str | None = Field(default=None, max_length=64)
    name_en: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    wechat_id: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=128)
    city: str | None = Field(default=None, max_length=80)
    basic_visibility: ProfileVisibility = "classmates"
    contact_visibility: ProfileVisibility = "private"
    details_visibility: ProfileVisibility = "private"

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

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("请填写姓名")
        return value.strip()

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value: str | None) -> str | None:
        return (value or "").strip().removesuffix("市").strip() or None


class OrganizationOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    parent_id: int | None
    entry_year: int | None = None


class MissingClassReport(BaseModel):
    note: str = Field(min_length=2, max_length=200)


class MyAffiliation(BaseModel):
    class_id: int | None = None
    org_path: str = ""
    pending_class_id: int | None = None
    pending_org_path: str = ""


class AffiliationRequest(BaseModel):
    class_id: int
    name: str | None = Field(default=None, max_length=64)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("请填写姓名")
        return value.strip()
