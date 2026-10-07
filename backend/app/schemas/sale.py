from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


PAYMENT_METHODS = {
    "cash",
    "card",
    "bank",
    "other",
}


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)

    @field_validator("quantity", "unit_price", "discount")
    @classmethod
    def normalize_decimal(cls, value):
        if value is None:
            return value
        return Decimal(str(value))


class SalePaymentCreate(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)
    received_amount: Decimal | None = Field(default=None, ge=0)
    reference: str | None = None
    notes: str | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in PAYMENT_METHODS:
            raise ValueError(
                "Payment method must be cash, card, bank or other."
            )

        return value


class SaleCreate(BaseModel):
    customer_id: UUID | None = None
    items: list[SaleItemCreate] = Field(min_length=1)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    payments: list[SalePaymentCreate] = Field(default_factory=list)
    notes: str | None = None


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name: str
    product_code: str | None
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    total: Decimal


class SalePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    method: str
    amount: Decimal
    received_amount: Decimal | None
    change_amount: Decimal | None
    reference: str | None
    notes: str | None


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    receipt_number: str
    customer_id: UUID | None
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    paid_amount: Decimal
    credit_amount: Decimal
    status: str
    notes: str | None
    created_at: datetime
    items: list[SaleItemResponse] = Field(default_factory=list)
    payments: list[SalePaymentResponse] = Field(default_factory=list)


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    total: int
    page: int
    page_size: int


class SaleCalculationRequest(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)


class SaleCalculationResponse(BaseModel):
    subtotal: Decimal
    discount: Decimal
    total: Decimal
