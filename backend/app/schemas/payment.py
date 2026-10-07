from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PaymentCreate(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)
    reference: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        value = value.lower().strip()

        allowed = {
            "cash",
            "bank_transfer",
            "card",
            "other",
        }

        if value not in allowed:
            raise ValueError(
                "Payment method must be cash, bank_transfer, card, or other."
            )

        return value


class PaymentResponse(BaseModel):
    id: UUID
    sale_id: UUID
    method: str
    amount: Decimal
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentSummary(BaseModel):
    total_due: Decimal
    total_paid: Decimal
    outstanding: Decimal
    change: Decimal
    payment_status: str
