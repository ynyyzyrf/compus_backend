from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    ActivityStatus,
    CheckinMethod,
    PhotoStatus,
    SignupStatus,
)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    cover_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    location: Mapped[str] = mapped_column(String(200))
    organizer: Mapped[str | None] = mapped_column(String(200))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    signup_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    signup_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(32), default=ActivityStatus.DRAFT, server_default=ActivityStatus.DRAFT
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ActivitySignup(Base):
    __tablename__ = "activity_signups"
    __table_args__ = (
        UniqueConstraint("activity_id", "user_id", name="signup_activity_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    phone: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(32), default=SignupStatus.SIGNED, server_default=SignupStatus.SIGNED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ActivityCheckin(Base):
    __tablename__ = "activity_checkins"
    __table_args__ = (
        UniqueConstraint("activity_id", "user_id", name="checkin_activity_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    signup_id: Mapped[int | None] = mapped_column(
        ForeignKey("activity_signups.id", ondelete="SET NULL")
    )
    checkin_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    checkin_method: Mapped[str] = mapped_column(
        String(32), default=CheckinMethod.QRCODE, server_default=CheckinMethod.QRCODE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    uploader_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    file_url: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(
        String(32), default=PhotoStatus.PENDING, server_default=PhotoStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
