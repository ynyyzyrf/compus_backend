"""Allow multiple reviewers per class, assigned by super administrators."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_administrators",
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_class_administrators_user_id", "class_administrators", ["user_id"])


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'user' WHERE role = 'class_admin'")
    op.drop_table("class_administrators")
