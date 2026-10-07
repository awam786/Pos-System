from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
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
from app.permissions import Permission


router = APIRouter(
    prefix="/held-sales",
    tags=["Held Sales"],
)


async def serialize(
    db: DbSession,
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
    db: DbSession,
    current_user: CurrentUser,
) -> HeldSaleResponse:
    require_permission(
        current_user,
        Permission.SALES,
    )

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
    db: DbSession,
    current_user: CurrentUser,
) -> HeldSaleListResponse:
    require_permission(
        current_user,
        Permission.SALES,
    )

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
    db: DbSession,
    current_user: CurrentUser,
) -> HeldSaleResponse:
    require_permission(
        current_user,
        Permission.SALES,
    )

    held_sale = await get_held_sale(
        db,
        current_user.shop_id,
        held_sale_id,
    )

    if held_sale is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Held sale not found.",
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
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    require_permission(
        current_user,
        Permission.SALES,
    )

    await delete_held_sale(
        db,
        current_user.shop_id,
        held_sale_id,
    )
