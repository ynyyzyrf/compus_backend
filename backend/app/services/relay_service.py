"""Relay: lightweight form collection (PRD §16)."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import RelayStatus
from app.models.relay import Relay, RelayField, RelayResponse
from app.models.user import User


class RelayError(Exception):
    pass


class RelayClosed(RelayError):
    pass


class RelayAlreadySubmitted(RelayError):
    pass


class RelayValidationError(RelayError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_closed(relay: Relay) -> bool:
    if relay.status == RelayStatus.CLOSED:
        return True
    if relay.deadline is None:
        return False
    deadline = relay.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return _now() > deadline


def _field_to_dict(field: RelayField) -> dict:
    return {
        "id": field.id,
        "label": field.label,
        "field_type": field.field_type,
        "required": field.required,
        "options": field.options_json,
        "sort_order": field.sort_order,
    }


def _response_counts(db: Session, relay_ids: list[int]) -> dict[int, int]:
    if not relay_ids:
        return {}
    return dict(
        db.execute(
            select(RelayResponse.relay_id, func.count())
            .where(RelayResponse.relay_id.in_(relay_ids))
            .group_by(RelayResponse.relay_id)
        ).all()
    )


def list_relays(
    db: Session,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    include_closed: bool = True,
) -> tuple[list[Relay], int, dict[int, int]]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    stmt = select(Relay)
    if status:
        stmt = stmt.where(Relay.status == status)
    elif not include_closed:
        stmt = stmt.where(Relay.status == RelayStatus.OPEN)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(Relay.created_at.desc(), Relay.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    counts = _response_counts(db, [row.id for row in rows])
    return list(rows), total, counts


def relay_fields(db: Session, relay_id: int) -> list[RelayField]:
    return list(
        db.scalars(
            select(RelayField)
            .where(RelayField.relay_id == relay_id)
            .order_by(RelayField.sort_order, RelayField.id)
        )
    )


def get_relay_detail(db: Session, relay_id: int, user: User) -> dict | None:
    relay = db.get(Relay, relay_id)
    if relay is None:
        return None
    response = db.execute(
        select(RelayResponse).where(
            RelayResponse.relay_id == relay_id,
            RelayResponse.user_id == user.id,
        )
    ).scalar_one_or_none()
    counts = _response_counts(db, [relay_id])
    return relay_to_detail(
        db,
        relay,
        response_count=counts.get(relay_id, 0),
        my_response=response.response_json if response else None,
    )


def relay_to_list_item(relay: Relay, response_count: int = 0) -> dict:
    return {
        "id": relay.id,
        "title": relay.title,
        "description": relay.description,
        "deadline": relay.deadline,
        "status": relay.status,
        "response_count": response_count,
        "created_at": relay.created_at,
    }


def relay_to_detail(
    db: Session,
    relay: Relay,
    response_count: int = 0,
    my_response: dict[str, Any] | None = None,
) -> dict:
    return {
        **relay_to_list_item(relay, response_count),
        "fields": [_field_to_dict(field) for field in relay_fields(db, relay.id)],
        "my_response": my_response,
    }


def _validate_response(fields: list[RelayField], response: dict[str, Any]) -> None:
    by_label = {field.label: field for field in fields}
    for field in fields:
        value = response.get(field.label)
        if field.required and (value is None or value == "" or value == []):
            raise RelayValidationError(f"{field.label} 為必填")
        if value is None or value == "":
            continue
        options = field.options_json or []
        if field.field_type == "number" and not isinstance(value, (int, float)):
            raise RelayValidationError(f"{field.label} 必須是數字")
        if field.field_type == "radio" and options and value not in options:
            raise RelayValidationError(f"{field.label} 選項無效")
        if field.field_type == "checkbox":
            if not isinstance(value, list):
                raise RelayValidationError(f"{field.label} 必須是多選列表")
            if options and any(item not in options for item in value):
                raise RelayValidationError(f"{field.label} 選項無效")

    unknown = set(response) - set(by_label)
    if unknown:
        raise RelayValidationError(f"未知字段: {', '.join(sorted(unknown))}")


def submit_response(db: Session, relay_id: int, user: User, response: dict[str, Any]) -> RelayResponse:
    relay = db.get(Relay, relay_id)
    if relay is None:
        raise RelayError("接龍不存在")
    if _is_closed(relay):
        raise RelayClosed("接龍已截止")
    exists = db.execute(
        select(RelayResponse.id).where(
            RelayResponse.relay_id == relay_id,
            RelayResponse.user_id == user.id,
        )
    ).first()
    if exists is not None:
        raise RelayAlreadySubmitted("已提交，無需重複")
    fields = relay_fields(db, relay_id)
    _validate_response(fields, response)
    row = RelayResponse(relay_id=relay_id, user_id=user.id, response_json=response)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_relay(db: Session, payload, creator: User) -> Relay:
    relay = Relay(
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        status=payload.status,
        created_by=creator.id,
    )
    db.add(relay)
    db.flush()
    _replace_fields(db, relay.id, payload.fields)
    db.commit()
    db.refresh(relay)
    return relay


def update_relay(db: Session, relay_id: int, payload) -> Relay | None:
    relay = db.get(Relay, relay_id)
    if relay is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    fields = data.pop("fields", None)
    for key, value in data.items():
        setattr(relay, key, value)
    if fields is not None:
        _replace_fields(db, relay_id, fields)
    db.commit()
    db.refresh(relay)
    return relay


def delete_relay(db: Session, relay_id: int) -> bool:
    relay = db.get(Relay, relay_id)
    if relay is None:
        return False
    db.delete(relay)
    db.commit()
    return True


def _replace_fields(db: Session, relay_id: int, fields) -> None:
    db.execute(RelayField.__table__.delete().where(RelayField.relay_id == relay_id))
    for index, field in enumerate(fields):
        db.add(
            RelayField(
                relay_id=relay_id,
                label=field.label,
                field_type=field.field_type,
                required=field.required,
                options_json=field.options,
                sort_order=field.sort_order if field.sort_order is not None else index,
            )
        )
    db.flush()


def response_out(row: RelayResponse) -> dict:
    return {
        "id": row.id,
        "relay_id": row.relay_id,
        "user_id": row.user_id,
        "response": row.response_json,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_responses(db: Session, relay_id: int) -> tuple[list[dict], int]:
    rows = db.execute(
        select(RelayResponse, User)
        .join(User, User.id == RelayResponse.user_id)
        .where(RelayResponse.relay_id == relay_id)
        .order_by(RelayResponse.created_at.desc(), RelayResponse.id.desc())
    ).all()
    items = [
        {
            "id": response.id,
            "user_id": user.id,
            "user_name": user.name,
            "response": response.response_json,
            "created_at": response.created_at,
            "updated_at": response.updated_at,
        }
        for response, user in rows
    ]
    return items, len(items)
