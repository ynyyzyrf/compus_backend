"""Add class years, discovery preferences and alumni connections."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("entry_year", sa.Integer()))
    op.add_column(
        "users", sa.Column("alumni_discoverable", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column("users", sa.Column("missing_class_note", sa.String(200)))
    op.create_table(
        "alumni_connections",
        sa.Column("user_low_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_high_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sender_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("low_shares_wechat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("high_shares_wechat", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("user_low_id < user_high_id", name="alumni_connection_order"),
        sa.CheckConstraint("sender_id IN (user_low_id, user_high_id)", name="alumni_connection_sender"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'declined')", name="alumni_connection_status"),
    )
    op.create_index("ix_alumni_connections_user_high_id", "alumni_connections", ["user_high_id"])
    op.create_index("ix_alumni_connections_sender_id", "alumni_connections", ["sender_id"])


def downgrade() -> None:
    op.drop_table("alumni_connections")
    op.drop_column("users", "missing_class_note")
    op.drop_column("users", "alumni_discoverable")
    op.drop_column("organizations", "entry_year")
