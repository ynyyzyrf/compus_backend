"""Read / update the current user's profile."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.profile import MyProfileUpdate


def get_my_profile(db: Session, user: User) -> User:
    return user


def update_my_profile(db: Session, user: User, payload: MyProfileUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
