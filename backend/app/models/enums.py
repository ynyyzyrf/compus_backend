"""String constants stored in DB columns (kept as plain strings, matching PRD §23)."""

from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    SUPER_ADMIN = "super_admin"


class Status(StrEnum):
    ACTIVE = "active"      # 正常
    DISABLED = "disabled"  # 停用


class OrgType(StrEnum):
    SCHOOL = "school"
    COLLEGE = "college"
    DEPARTMENT = "department"
    CLASS = "class"


class DirectoryScope(StrEnum):
    """directory_permissions.scope_type"""

    CLASS = "class"
    DEPARTMENT = "department"
    COLLEGE = "college"


class ActivityStatus(StrEnum):
    DRAFT = "draft"
    SIGNING = "signing"        # 報名中
    UPCOMING = "upcoming"      # 即將開始
    ONGOING = "ongoing"        # 進行中
    FINISHED = "finished"      # 已結束


class SignupStatus(StrEnum):
    SIGNED = "signed"
    CANCELLED = "cancelled"


class CheckinMethod(StrEnum):
    QRCODE = "qrcode"


class PhotoStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArticleType(StrEnum):
    NEWS = "news"
    ANNOUNCEMENT = "announcement"
    NOTICE = "notice"


class ArticleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    OFFLINE = "offline"


class RelayStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class RelayFieldType(StrEnum):
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE = "date"
    IMAGE = "image"
