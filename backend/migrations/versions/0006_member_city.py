"""Add the optional city used by directory search."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("city", sa.String(80)))


def downgrade() -> None:
    op.drop_column("users", "city")
