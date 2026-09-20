from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class MyProfile(BaseModel):
    """Full profile payload for the current user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_en: str | None = None
    avatar_url: str | None = None

    # contact
    phone: str | None = None
    wechat_id: str | None = None
    email: str | None = None

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
            raise ValueError("請填寫姓名")
        return value.strip()
