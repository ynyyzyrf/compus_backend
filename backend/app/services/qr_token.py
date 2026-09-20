"""Short-lived signed token for QR-code activity checkin.

The admin endpoint issues a token bound to ``activity_id``. Users scan the
displayed QR code; the mini-program then POSTs the token to the user-side
checkin endpoint, which validates activity + duplicate + signup.
"""

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

_ALGORITHM = "HS256"
_DEFAULT_TTL = timedelta(hours=8)


def issue_checkin_token(activity_id: int, ttl: timedelta = _DEFAULT_TTL) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    exp = now + ttl
    payload = {"sub": "checkin", "aid": activity_id, "iat": now, "exp": exp}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)
    return token, exp


def decode_checkin_token(token: str, expected_activity_id: int) -> bool:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return False
    return (
        payload.get("sub") == "checkin"
        and int(payload.get("aid", -1)) == expected_activity_id
    )
