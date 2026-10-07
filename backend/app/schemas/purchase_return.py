from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)


class PurchaseCreate(BaseModel):
    supplier_id: UUID | None = None
    invoice_number: str | None = None
    items: list[PurchaseItemCreate] = Field(min_length=1)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    payment_method: str = "cash"
    payment_reference: str | None = None
    notes: str | None = None


class PurchaseItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    discount: Decimal
    total: Decimal


class PurchaseResponse(BaseModel):
    id: UUID
    supplier_id: UUID | None
    invoice_number: str | None
    status: str
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    paid_amount: Decimal
    notes: str | None
    created_at: datetime
    items: list[PurchaseItemResponse]


class ReturnItemCreate(BaseModel):
    sale_item_id: UUID
    quantity: Decimal = Field(gt=0)


class ReturnCreate(BaseModel):
    sale_id: UUID
    items: list[ReturnItemCreate] = Field(min_length=1)
    refund_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    reason: str | None = None


class ReturnItemResponse(BaseModel):
    id: UUID
    sale_item_id: UUID
    product_id: UUID
    quantity: Decimal
    amount: Decimal


class ReturnResponse(BaseModel):
    id: UUID
    sale_id: UUID
    status: str
    total: Decimal
    refund_amount: Decimal
    reason: str | None
    created_at: datetime
    items: list[ReturnItemResponse]
