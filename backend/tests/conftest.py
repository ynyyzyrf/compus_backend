import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure backend/ is importable when running pytest from the backend dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.models import Base  # noqa: E402,F401  (import every model)
from app.seeds.seed_dev import (  # noqa: E402
    build_orgs,
    build_permissions,
    build_users,
)


def _ensure_test_database() -> str:
    url = settings.test_database_url or settings.database_url
    if not settings.test_database_url:
        return url

    # The test DB is created by the docker init script on first volume init;
    # create it here too in case the volume predates that script.
    admin_engine = create_engine(
        settings.database_url, isolation_level="AUTOCOMMIT", future=True
    )
    db_name = url.rsplit("/", 1)[-1]
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()
    return url


@pytest.fixture(scope="session")
def engine():
    url = _ensure_test_database()
    eng = create_engine(url, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionTesting = sessionmaker(
        bind=connection, autoflush=False, autocommit=False, future=True
    )
    session = SessionTesting()

    # Seed inside the per-test transaction; rolled back afterwards.
    _, index = build_orgs(session)
    build_permissions(session, index)
    build_users(session, index)
    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def ctx(db) -> SimpleNamespace:
    """Convenient handles to seeded org/user rows by name."""
    from sqlalchemy import select

    from app.models.organization import Membership, Organization
    from app.models.user import User

    def user(name):
        return db.scalars(select(User).where(User.name == name)).one()

    def class_id_for(user_name):
        member = db.scalars(select(User).where(User.name == user_name)).one()
        return db.scalars(
            select(Membership.organization_id).where(
                Membership.user_id == member.id, Membership.is_primary.is_(True)
            )
        ).one()

    def org_by_name(name, parent_id):
        stmt = select(Organization).where(Organization.name == name)
        if parent_id is None:
            stmt = stmt.where(Organization.parent_id.is_(None))
        else:
            stmt = stmt.where(Organization.parent_id == parent_id)
        return db.scalars(stmt).one()

    return SimpleNamespace(
        db=db, user=user, class_id_for=class_id_for, org_by_name=org_by_name
    )
