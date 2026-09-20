from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.relay import (
    RelayDetail,
    RelayListItem,
    RelayResponseCreate,
    RelayResponseOut,
)
from app.services import relay_service

router = APIRouter(prefix="/relays", tags=["relays"])


@router.get("", response_model=list[RelayListItem])
def list_relays(
    _: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|closed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> list[RelayListItem]:
    rows, _, counts = relay_service.list_relays(
        db, status=status_filter, page=page, page_size=page_size
    )
    return [RelayListItem(**relay_service.relay_to_list_item(row, counts.get(row.id, 0))) for row in rows]


@router.get("/{relay_id}", response_model=RelayDetail)
def get_relay(relay_id: int, current_user: CurrentUser, db: DbSession) -> RelayDetail:
    payload = relay_service.get_relay_detail(db, relay_id, current_user)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="接龍不存在")
    return RelayDetail(**payload)


@router.post("/{relay_id}/responses", response_model=RelayResponseOut, status_code=status.HTTP_201_CREATED)
def submit_relay_response(
    relay_id: int,
    payload: RelayResponseCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> RelayResponseOut:
    try:
        row = relay_service.submit_response(db, relay_id, current_user, payload.response)
    except relay_service.RelayAlreadySubmitted as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except relay_service.RelayClosed as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except relay_service.RelayValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except relay_service.RelayError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return RelayResponseOut(**relay_service.response_out(row))
