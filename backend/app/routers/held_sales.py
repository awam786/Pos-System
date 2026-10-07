from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, get_current_user
from app.models.user import User
from app.permissions import Permission
from app.schemas.held_sale import (
    HeldSaleCreate,
    HeldSaleItemResponse,
    HeldSaleListResponse,
    HeldSaleResponse,
)
from app.services.held_sales import (
    create_held_sale,
    delete_held_sale,
    get_held_sale,
    get_held_sale_items,
    list_held_sales,
)
from app.services.permissions import require_permission


router = APIRouter(
    prefix="/held-sales",
    tags=["Held Sales"],
)


async def serialize(
    db: AsyncSession,
    held_sale,
) -> HeldSaleResponse:
    items = await get_held_sale_items(
        db,
        held_sale.id,
    )

    return HeldSaleResponse(
        id=held_sale.id,
        customer_id=held_sale.customer_id,
        reference=held_sale.reference,
        notes=held_sale.notes,
        created_at=held_sale.created_at,
        items=[
            HeldSaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount,
            )
            for item in items
        ],
    )


@router.post(
    "",
    response_model=HeldSaleResponse,
    status_code=201,
)
async def create(
    payload: HeldSaleCreate,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    held_sale = await create_held_sale(
        db,
        current_user.shop_id,
        current_user.id,
        payload,
    )

    return await serialize(
        db,
        held_sale,
    )


@router.get(
    "",
    response_model=HeldSaleListResponse,
)
async def list_all(
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    items, total = await list_held_sales(
        db,
        current_user.shop_id,
    )

    serialized = [
        await serialize(db, item)
        for item in items
    ]

    return HeldSaleListResponse(
        items=serialized,
        total=total,
    )


@router.get(
    "/{held_sale_id}",
    response_model=HeldSaleResponse,
)
async def get(
    held_sale_id: UUID,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    held_sale = await get_held_sale(
        db,
        current_user.shop_id,
        held_sale_id,
    )

    return await serialize(
        db,
        held_sale,
    )


@router.delete(
    "/{held_sale_id}",
    status_code=204,
)
async def delete(
    held_sale_id: UUID,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    await delete_held_sale(
        db,
        current_user.shop_id,
        held_sale_id,
    )
