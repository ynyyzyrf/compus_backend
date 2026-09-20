from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Role, Status


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    openid: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    unionid: Mapped[str | None] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    # ---- contact ----
    phone: Mapped[str | None] = mapped_column(String(32))
    wechat_id: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(128))
    bio: Mapped[str | None] = mapped_column(Text)

    # ---- bilingual display name + profession ----
    name_en: Mapped[str | None] = mapped_column(String(100))
    profession: Mapped[str | None] = mapped_column(String(128))
    profession_en: Mapped[str | None] = mapped_column(String(128))

    # ---- company / position ----
    company_name: Mapped[str | None] = mapped_column(String(200))
    company_address: Mapped[str | None] = mapped_column(String(500))
    company_founded_at: Mapped[date | None] = mapped_column(Date)
    position: Mapped[str | None] = mapped_column(String(100))

    # ---- business narrative ----
    business_description: Mapped[str | None] = mapped_column(Text)
    referrals_needed: Mapped[str | None] = mapped_column(Text)
    personal_experience: Mapped[str | None] = mapped_column(Text)
    resources_offered: Mapped[str | None] = mapped_column(Text)

    # ---- chamber / 商會 membership (BNI / EO / Rotary / local chamber) ----
    chamber_chapter: Mapped[str | None] = mapped_column(String(128))
    chamber_member_no: Mapped[str | None] = mapped_column(String(64))
    chamber_join_date: Mapped[date | None] = mapped_column(Date)
    chamber_score: Mapped[int | None] = mapped_column(Integer)

    # ---- access control ----
    role: Mapped[str] = mapped_column(String(32), default=Role.USER, server_default=Role.USER)
    status: Mapped[str] = mapped_column(
        String(32), default=Status.ACTIVE, server_default=Status.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
