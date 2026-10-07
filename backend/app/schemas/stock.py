from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class InventoryDashboardItem(BaseModel):
    product_id: str
    product_name: str
    sku: str | None = None
    stock_quantity: Decimal
    minimum_stock: Decimal
    maximum_stock: Decimal | None = None
    selling_price: Decimal
    purchase_price: Decimal
    low_stock: bool
    out_of_stock: bool


class InventoryDashboardResponse(BaseModel):
    total_products: int
    active_products: int
    low_stock_products: int
    out_of_stock_products: int
    items: list[InventoryDashboardItem]
