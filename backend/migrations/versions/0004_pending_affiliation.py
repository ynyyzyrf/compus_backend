"""Store organization applications separately from approved memberships."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pending_class_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("affiliation_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_users_pending_class_id", "users", "organizations", ["pending_class_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_users_pending_class_id", "users", ["pending_class_id"])


def downgrade() -> None:
    op.drop_index("ix_users_pending_class_id", table_name="users")
    op.drop_constraint("fk_users_pending_class_id", "users", type_="foreignkey")
    op.drop_column("users", "affiliation_requested_at")
    op.drop_column("users", "pending_class_id")
