from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PhotoCreate(BaseModel):
    file_url: str = Field(min_length=1, max_length=512)


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    uploader_id: int | None
    file_url: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None


class PhotoPage(BaseModel):
    items: list[PhotoOut]
    total: int
    page: int
    page_size: int
