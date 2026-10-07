from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class HeldSaleItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0)


class HeldSaleCreate(BaseModel):
    customer_id: UUID | None = None
    reference: str | None = None
    notes: str | None = None
    items: list[HeldSaleItemCreate] = Field(min_length=1)


class HeldSaleItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal


class HeldSaleResponse(BaseModel):
    id: UUID
    customer_id: UUID | None
    reference: str | None
    notes: str | None
    created_at: datetime
    items: list[HeldSaleItemResponse]


class HeldSaleListResponse(BaseModel):
    items: list[HeldSaleResponse]
    total: int
