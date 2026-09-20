from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import DbSession, SuperAdmin
from app.schemas.relay import (
    RelayAdminPage,
    RelayCreate,
    RelayDetail,
    RelayResponsePage,
    RelayUpdate,
)
from app.services import relay_service

router = APIRouter(prefix="/admin/relays", tags=["admin/relays"])


@router.get("", response_model=RelayAdminPage)
def list_admin_relays(
    _: SuperAdmin,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|closed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> RelayAdminPage:
    rows, total, counts = relay_service.list_relays(
        db, status=status_filter, page=page, page_size=page_size
    )
    return RelayAdminPage(
        items=[relay_service.relay_to_list_item(row, counts.get(row.id, 0)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RelayDetail, status_code=status.HTTP_201_CREATED)
def create_relay(payload: RelayCreate, admin: SuperAdmin, db: DbSession) -> RelayDetail:
    relay = relay_service.create_relay(db, payload, admin)
    return RelayDetail(**relay_service.relay_to_detail(db, relay))


@router.put("/{relay_id}", response_model=RelayDetail)
def update_relay(relay_id: int, payload: RelayUpdate, _: SuperAdmin, db: DbSession) -> RelayDetail:
    relay = relay_service.update_relay(db, relay_id, payload)
    if relay is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="接龍不存在")
    counts = relay_service._response_counts(db, [relay_id])
    return RelayDetail(**relay_service.relay_to_detail(db, relay, counts.get(relay_id, 0)))


@router.delete("/{relay_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relay(relay_id: int, _: SuperAdmin, db: DbSession) -> None:
    if not relay_service.delete_relay(db, relay_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="接龍不存在")


@router.get("/{relay_id}/responses", response_model=RelayResponsePage)
def list_relay_responses(relay_id: int, _: SuperAdmin, db: DbSession) -> RelayResponsePage:
    if db.get(relay_service.Relay, relay_id) is None:  # type: ignore[attr-defined]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="接龍不存在")
    items, total = relay_service.list_responses(db, relay_id)
    return RelayResponsePage(items=items, total=total)
