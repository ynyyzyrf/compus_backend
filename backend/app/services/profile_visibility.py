from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.models.connection import AlumniConnection


def accepted_peers(db: Session, viewer_id: int) -> set[int]:
    peer = case(
        (AlumniConnection.user_low_id == viewer_id, AlumniConnection.user_high_id),
        else_=AlumniConnection.user_low_id,
    )
    return set(db.scalars(select(peer).where(
        or_(AlumniConnection.user_low_id == viewer_id, AlumniConnection.user_high_id == viewer_id),
        AlumniConnection.status == "accepted",
    )))


def allows(audience: str, *, own: bool, same_class: bool, friend: bool) -> bool:
    return own or (audience in ("friends", "classmates") and friend) or (audience == "classmates" and same_class)
