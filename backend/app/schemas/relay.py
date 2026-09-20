from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RelayFieldBase(BaseModel):
    label: str = Field(min_length=1, max_length=128)
    field_type: str = Field(pattern="^(text|textarea|number|radio|checkbox|date|image)$")
    required: bool = False
    options: list[str] | None = None
    sort_order: int = 0


class RelayFieldOut(RelayFieldBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RelayListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    deadline: datetime | None
    status: str
    response_count: int = 0
    created_at: datetime


class RelayDetail(RelayListItem):
    fields: list[RelayFieldOut]
    my_response: dict[str, Any] | None = None


class RelayResponseCreate(BaseModel):
    response: dict[str, Any] = Field(default_factory=dict)


class RelayResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relay_id: int
    user_id: int
    response: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RelayCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    status: str = Field(default="open", pattern="^(open|closed)$")
    fields: list[RelayFieldBase] = Field(min_length=1)


class RelayUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    status: str | None = Field(default=None, pattern="^(open|closed)$")
    fields: list[RelayFieldBase] | None = None


class RelayAdminPage(BaseModel):
    items: list[RelayListItem]
    total: int
    page: int
    page_size: int


class RelayResponseRow(BaseModel):
    id: int
    user_id: int
    user_name: str
    response: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RelayResponsePage(BaseModel):
    items: list[RelayResponseRow]
    total: int
