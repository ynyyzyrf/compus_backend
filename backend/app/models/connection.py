from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlumniConnection(Base):
    """One request or accepted friendship for each pair of users."""

    __tablename__ = "alumni_connections"
    __table_args__ = (
        CheckConstraint("user_low_id < user_high_id", name="alumni_connection_order"),
        CheckConstraint(
            "sender_id IN (user_low_id, user_high_id)", name="alumni_connection_sender"
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined')", name="alumni_connection_status"
        ),
    )

    user_low_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    user_high_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    sender_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    low_shares_wechat: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    high_shares_wechat: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class AlumniMessage(Base):
    __tablename__ = "alumni_messages"
    __table_args__ = (
        ForeignKeyConstraint(["user_low_id", "user_high_id"], ["alumni_connections.user_low_id", "alumni_connections.user_high_id"], ondelete="CASCADE"),
        CheckConstraint("sender_id IN (user_low_id, user_high_id)", name="alumni_message_sender"),
        UniqueConstraint("user_low_id", "user_high_id", "sender_id", "client_id", name="alumni_message_dedupe"),
        Index("ix_alumni_messages_pair_id", "user_low_id", "user_high_id", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_low_id: Mapped[int] = mapped_column(BigInteger)
    user_high_id: Mapped[int] = mapped_column(BigInteger)
    sender_id: Mapped[int] = mapped_column(BigInteger)
    client_id: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
