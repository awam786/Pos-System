from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import HeldSale, HeldSaleItem, Product
from app.schemas.held_sale import HeldSaleCreate
from app.services.sales import calculate_discount, calculate_line, money, quantity


async def create_held_sale(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID,
    request: HeldSaleCreate,
) -> HeldSale:
    if not request.items:
        raise HTTPException(
            status_code=400,
            detail="A held sale must contain at least one item.",
        )

    products_result = await db.execute(
        select(Product).where(
            Product.shop_id == shop_id,
            Product.id.in_(
                [item.product_id for item in request.items]
            ),
        )
    )

    products = {
        product.id: product
        for product in products_result.scalars().all()
    }

    if len(products) != len(
        {item.product_id for item in request.items}
    ):
        raise HTTPException(
            status_code=400,
            detail="One or more products were not found.",
        )

    subtotal = Decimal("0.00")
    item_discount_total = Decimal("0.00")

    calculated = []

    for item in request.items:
        product = products[item.product_id]

        if not product.active:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product.name}' is inactive.",
            )

        qty = quantity(item.quantity)

        unit_price, discount, line_total = calculate_line(
            product,
            item,
        )

        subtotal += money(unit_price * qty)
        item_discount_total += discount

        calculated.append(
            (
                item,
                product,
                qty,
                unit_price,
                discount,
                line_total,
            )
        )

    subtotal = money(subtotal)

    bill_discount = calculate_discount(
        subtotal - item_discount_total,
        request.bill_discount_type,
        request.bill_discount_value,
    )

    total = money(
        subtotal - item_discount_total - bill_discount
    )

    held_sale = HeldSale(
        shop_id=shop_id,
        user_id=user_id,
        customer_id=request.customer_id,
        subtotal=subtotal,
        discount_type=request.bill_discount_type,
        discount_value=money(request.bill_discount_value),
        total=total,
        notes=request.notes,
    )

    db.add(held_sale)
    await db.flush()

    for (
        item,
        product,
        qty,
        unit_price,
        discount,
        line_total,
    ) in calculated:
        db.add(
            HeldSaleItem(
                held_sale_id=held_sale.id,
                product_id=product.id,
                quantity=qty,
                unit_price=unit_price,
                discount_type=item.discount_type,
                discount_value=money(item.discount_value),
                discount_amount=discount,
                line_total=line_total,
            )
        )

    await db.commit()

    return await get_held_sale(
        db,
        shop_id,
        held_sale.id,
    )


async def get_held_sale(
    db: AsyncSession,
    shop_id: UUID,
    held_sale_id: UUID,
) -> HeldSale:
    result = await db.execute(
        select(HeldSale)
        .options(
            selectinload(HeldSale.items),
        )
        .where(
            HeldSale.id == held_sale_id,
            HeldSale.shop_id == shop_id,
        )
    )

    held_sale = result.scalar_one_or_none()

    if not held_sale:
        raise HTTPException(
            status_code=404,
            detail="Held sale not found.",
        )

    return held_sale


async def list_held_sales(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID | None = None,
) -> tuple[list[HeldSale], int]:
    conditions = [
        HeldSale.shop_id == shop_id,
    ]

    if user_id:
        conditions.append(HeldSale.user_id == user_id)

    count_result = await db.execute(
        select(func.count(HeldSale.id)).where(*conditions)
    )

    total = count_result.scalar_one() or 0

    result = await db.execute(
        select(HeldSale)
        .options(
            selectinload(HeldSale.items),
        )
        .where(*conditions)
        .order_by(HeldSale.created_at.desc())
    )

    return list(result.scalars().all()), total


async def delete_held_sale(
    db: AsyncSession,
    shop_id: UUID,
    held_sale_id: UUID,
) -> None:
    held_sale = await get_held_sale(
        db,
        shop_id,
        held_sale_id,
    )

    await db.delete(held_sale)
    await db.commit()
