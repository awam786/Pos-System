from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import HeldSale, HeldSaleItem
from app.models.partner import Customer
from app.models.product import Product
from app.schemas.held_sale import HeldSaleCreate


async def create_held_sale(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID,
    payload: HeldSaleCreate,
) -> HeldSale:
    if payload.customer_id:
        customer = await db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.shop_id == shop_id,
            )
        )

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

    for item in payload.items:
        product = await db.scalar(
            select(Product).where(
                Product.id == item.product_id,
                Product.shop_id == shop_id,
                Product.active.is_(True),
            )
        )

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more products were not found.",
            )

    held_sale = HeldSale(
        shop_id=shop_id,
        user_id=user_id,
        customer_id=payload.customer_id,
        reference=payload.reference,
        notes=payload.notes,
    )

    db.add(held_sale)
    await db.flush()

    for item in payload.items:
        db.add(
            HeldSaleItem(
                held_sale_id=held_sale.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount,
            )
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return held_sale


async def get_held_sale(
    db: AsyncSession,
    shop_id: UUID,
    held_sale_id: UUID,
) -> HeldSale:
    held_sale = await db.scalar(
        select(HeldSale).where(
            HeldSale.id == held_sale_id,
            HeldSale.shop_id == shop_id,
        )
    )

    if not held_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Held sale not found.",
        )

    return held_sale


async def get_held_sale_items(
    db: AsyncSession,
    held_sale_id: UUID,
) -> list[HeldSaleItem]:
    result = await db.execute(
        select(HeldSaleItem)
        .where(
            HeldSaleItem.held_sale_id == held_sale_id
        )
        .order_by(HeldSaleItem.created_at.asc())
    )

    return list(result.scalars().all())


async def list_held_sales(
    db: AsyncSession,
    shop_id: UUID,
) -> tuple[list[HeldSale], int]:
    count_result = await db.execute(
        select(func.count(HeldSale.id)).where(
            HeldSale.shop_id == shop_id
        )
    )

    total = int(count_result.scalar() or 0)

    result = await db.execute(
        select(HeldSale)
        .where(HeldSale.shop_id == shop_id)
        .order_by(HeldSale.created_at.desc())
    )

    return list(result.scalars().all()), total


async def delete_held_sale(
    db: AsyncSession,
    shop_id: UUID,
    held_sale_id: UUID,
) -> None:
    await get_held_sale(
        db,
        shop_id,
        held_sale_id,
    )

    await db.execute(
        delete(HeldSale).where(
            HeldSale.id == held_sale_id,
            HeldSale.shop_id == shop_id,
        )
    )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
