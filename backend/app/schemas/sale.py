from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SaleItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_type: str = "none"
    discount_value: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"none", "fixed", "percentage"}:
            raise ValueError("Discount type must be none, fixed, or percentage.")
        return value


class SalePaymentCreate(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)
    reference: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"cash", "bank_transfer", "card", "other"}:
            raise ValueError(
                "Payment method must be cash, bank_transfer, card, or other."
            )
        return value


class SaleCreate(BaseModel):
    customer_id: Optional[UUID] = None
    items: list[SaleItemCreate] = Field(min_length=1)
    bill_discount_type: str = "none"
    bill_discount_value: Decimal = Field(default=Decimal("0"), ge=0)
    payments: list[SalePaymentCreate] = Field(default_factory=list)
    notes: Optional[str] = None
    cash_received: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator("bill_discount_type")
    @classmethod
    def validate_bill_discount_type(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"none", "fixed", "percentage"}:
            raise ValueError(
                "Bill discount type must be none, fixed, or percentage."
            )
        return value


class SaleItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    sku: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    line_total: Decimal


class SalePaymentResponse(BaseModel):
    id: UUID
    method: str
    amount: Decimal
    reference: Optional[str] = None
    notes: Optional[str] = None


class SaleResponse(BaseModel):
    id: UUID
    invoice_number: str
    customer_id: Optional[UUID] = None
    user_id: UUID
    subtotal: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    payment_status: str
    status: str
    notes: Optional[str] = None
    items: list[SaleItemResponse] = Field(default_factory=list)
    payments: list[SalePaymentResponse] = Field(default_factory=list)


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    total: int


class SaleSummaryResponse(BaseModel):
    subtotal: Decimal
    item_discount: Decimal
    bill_discount: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    change_amount: Decimal
    payment_status: str


class SaleCalculationRequest(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    bill_discount_type: str = "none"
    bill_discount_value: Decimal = Field(default=Decimal("0"), ge=0)


class SaleCalculationResponse(SaleSummaryResponse):
    items: list[SaleItemResponse]
