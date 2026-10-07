from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class HeldSaleItemCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_type: str = "none"
    discount_value: Decimal = Field(default=Decimal("0"), ge=0)


class HeldSaleCreate(BaseModel):
    customer_id: Optional[UUID] = None
    items: list[HeldSaleItemCreate] = Field(min_length=1)
    bill_discount_type: str = "none"
    bill_discount_value: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None


class HeldSaleItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    discount_type: str
    discount_value: Decimal
    line_total: Decimal


class HeldSaleResponse(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
    user_id: UUID
    subtotal: Decimal
    discount_type: str
    discount_value: Decimal
    total: Decimal
    notes: Optional[str] = None
    items: list[HeldSaleItemResponse] = Field(default_factory=list)


class HeldSaleListResponse(BaseModel):
    items: list[HeldSaleResponse]
    total: int
