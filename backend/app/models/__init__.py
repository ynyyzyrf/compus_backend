"""Import every model so SQLAlchemy metadata and Alembic autogenerate see them."""

from app.db.base import Base
from app.models.activity import (
    Activity,
    ActivityCheckin,
    ActivitySignup,
    Photo,
)
from app.models.content import Article, ArticleScope
from app.models.organization import (
    DirectoryPermission,
    Membership,
    Organization,
)
from app.models.relay import Relay, RelayField, RelayResponse
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Organization",
    "Membership",
    "DirectoryPermission",
    "Activity",
    "ActivitySignup",
    "ActivityCheckin",
    "Photo",
    "Article",
    "ArticleScope",
    "Relay",
    "RelayField",
    "RelayResponse",
]
