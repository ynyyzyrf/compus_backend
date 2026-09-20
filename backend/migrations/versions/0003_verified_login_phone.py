"""Add a separately verified, unique phone for account identity.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verified_phone", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False))
    op.create_index("ix_users_verified_phone", "users", ["verified_phone"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_verified_phone", table_name="users")
    op.drop_column("users", "phone_verified_at")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "verified_phone")
