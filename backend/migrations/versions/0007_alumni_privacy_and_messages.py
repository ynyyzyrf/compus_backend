"""Add card visibility and private messages between friends."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("basic_visibility", sa.String(12), server_default="classmates", nullable=False))
    for field in ("contact_visibility", "details_visibility"):
        op.add_column("users", sa.Column(field, sa.String(12), server_default="private", nullable=False))
    op.create_table(
        "alumni_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_low_id", sa.BigInteger(), nullable=False),
        sa.Column("user_high_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_low_id", "user_high_id"], ["alumni_connections.user_low_id", "alumni_connections.user_high_id"], ondelete="CASCADE"),
        sa.CheckConstraint("sender_id IN (user_low_id, user_high_id)", name="alumni_message_sender"),
        sa.UniqueConstraint("user_low_id", "user_high_id", "sender_id", "client_id", name="alumni_message_dedupe"),
    )
    op.create_index("ix_alumni_messages_pair_id", "alumni_messages", ["user_low_id", "user_high_id", "id"])
    op.execute("""
        UPDATE organizations
        SET entry_year = CAST(left(name, 4) AS integer)
        WHERE type = 'class' AND entry_year IS NULL AND name ~ '^(19|20)[0-9]{2} *[级級]'
    """)


def downgrade() -> None:
    op.drop_table("alumni_messages")
    for field in ("details_visibility", "contact_visibility", "basic_visibility"):
        op.drop_column("users", field)
