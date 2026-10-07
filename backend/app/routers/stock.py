from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import Product
from app.schemas.stock import (
    InventoryDashboardItem,
    InventoryDashboardResponse,
)


router = APIRouter(
    prefix="/stock",
    tags=["Stock"],
)


@router.get(
    "/dashboard",
    response_model=InventoryDashboardResponse,
)
async def stock_dashboard(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
):
    total_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.shop_id == current_user.shop_id,
        )
    )

    active_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
        )
    )

    low_stock_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
            Product.stock_quantity <= Product.minimum_stock,
            Product.stock_quantity > 0,
        )
    )

    out_stock_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
            Product.stock_quantity <= 0,
        )
    )

    result = await db.execute(
        select(Product)
        .where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
            Product.stock_quantity <= Product.minimum_stock,
        )
        .order_by(
            Product.stock_quantity.asc(),
            Product.name.asc(),
        )
        .limit(limit)
    )

    items = [
        InventoryDashboardItem(
            product_id=str(product.id),
            product_name=product.name,
            sku=product.sku,
            stock_quantity=product.stock_quantity,
            minimum_stock=product.minimum_stock,
            maximum_stock=product.maximum_stock,
            selling_price=product.selling_price,
            purchase_price=product.purchase_price,
            low_stock=(
                product.stock_quantity <= product.minimum_stock
                and product.stock_quantity > 0
            ),
            out_of_stock=product.stock_quantity <= 0,
        )
        for product in result.scalars().all()
    ]

    return InventoryDashboardResponse(
        total_products=int(total_result.scalar_one()),
        active_products=int(active_result.scalar_one()),
        low_stock_products=int(low_stock_result.scalar_one()),
        out_of_stock_products=int(out_stock_result.scalar_one()),
        items=items,
    )
