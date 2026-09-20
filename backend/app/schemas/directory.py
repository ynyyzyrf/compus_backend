from datetime import date

from pydantic import BaseModel, ConfigDict


class OrgNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    parent_id: int | None = None
    sort_order: int = 0
    member_count: int = 0


class DirectoryTreeOut(BaseModel):
    # nodes already scoped to what the viewer may see
    nodes: list[OrgNodeOut]
    # class / department / college / all
    scope_level: str


class MemberBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None = None
    class_id: int | None = None
    org_path: str = ""


class MemberDetail(BaseModel):
    """Full member card (PRD §23.1 + 商會業務名片字段)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None = None
    class_id: int | None = None
    org_path: str = ""

    # contact
    phone: str | None = None
    wechat_id: str | None = None
    email: str | None = None

    # bilingual display
    name_en: str | None = None

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

    # chamber / 商會 membership (BNI / EO / Rotary / local chamber)
    chamber_chapter: str | None = None
    chamber_member_no: str | None = None
    chamber_join_date: date | None = None
    chamber_score: int | None = None
