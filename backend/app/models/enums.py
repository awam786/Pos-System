from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    CASHIER = "cashier"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    BANK = "bank"
    OTHER = "other"
    CREDIT = "credit"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    PARTIAL = "partial"


class SaleStatus(StrEnum):
    COMPLETED = "completed"
    VOIDED = "voided"
    PARTIAL_RETURN = "partial_return"
    RETURNED = "returned"


class PurchaseStatus(StrEnum):
    RECEIVED = "received"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ReturnStatus(StrEnum):
    COMPLETED = "completed"
    REFUNDED = "refunded"
    PARTIAL = "partial"


class DiscountType(StrEnum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"


class StockMovementType(StrEnum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    DAMAGE = "damage"
    OPENING = "opening"


class CashMovementType(StrEnum):
    OPENING = "opening"
    SALE = "sale"
    REFUND = "refund"
    EXPENSE = "expense"
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"
    CLOSING = "closing"
