from enum import Enum


class LiveSessionStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    ENDED = "ENDED"


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    SOLD_OUT = "SOLD_OUT"


class CouponStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    NOT_STARTED = "NOT_STARTED"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class AlertType(str, Enum):
    COUPON_UNAVAILABLE = "COUPON_UNAVAILABLE"
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    LINK_BROKEN = "LINK_BROKEN"
    AFTER_SALES = "AFTER_SALES"
    UNKNOWN = "UNKNOWN"


class AlertSeverity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKED = "ACKED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK_WRITE = "LOW_RISK_WRITE"
    HIGH_RISK_WRITE = "HIGH_RISK_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
