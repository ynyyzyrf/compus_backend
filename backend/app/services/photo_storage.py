"""Storage driver boundary for activity photos.

The first implementation stores URL metadata only. Binary upload can later be
implemented by replacing this driver without changing the activity photo API.
"""

from dataclasses import dataclass

from app.core.config import settings


class StorageError(ValueError):
    pass


@dataclass(frozen=True)
class StoredImage:
    file_url: str


class StorageDriver:
    def normalize_image_url(self, file_url: str) -> StoredImage:
        raise NotImplementedError


class LocalStorageDriver(StorageDriver):
    def normalize_image_url(self, file_url: str) -> StoredImage:
        value = file_url.strip()
        if not value:
            raise StorageError("圖片地址不能為空")
        if len(value) > 512:
            raise StorageError("圖片地址過長")
        return StoredImage(file_url=value)


def get_storage_driver() -> StorageDriver:
    if settings.storage_driver != "local":
        raise StorageError(f"不支持的圖片存儲驅動: {settings.storage_driver}")
    return LocalStorageDriver()
