from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.permissions import Permission
from app.schemas.common import MessageResponse
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
    list_held_sales,
)
from app.services.permissions import require_permission


router = APIRouter(
    prefix="/held-sales",
    tags=["Held Sales"],
)


def serialize_held_sale(held_sale) -> HeldSaleResponse:
    return HeldSaleResponse(
        id=held_sale.id,
        customer_id=held_sale.customer_id,
        user_id=held_sale.user_id,
        subtotal=held_sale.subtotal,
        discount_type=held_sale.discount_type,
        discount_value=held_sale.discount_value,
        total=held_sale.total,
        notes=held_sale.notes,
        items=[
            HeldSaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_type=item.discount_type,
                discount_value=item.discount_value,
                line_total=item.line_total,
            )
            for item in held_sale.items
        ],
    )


@router.post(
    "",
    response_model=HeldSaleResponse,
)
async def create_held_sale_endpoint(
    payload: HeldSaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    held_sale = await create_held_sale(
        db,
        current_user.shop_id,
        current_user.id,
        payload,
    )

    return serialize_held_sale(held_sale)


@router.get(
    "",
    response_model=HeldSaleListResponse,
)
async def list_held_sales_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    held_sales, total = await list_held_sales(
        db,
        current_user.shop_id,
        current_user.id,
    )

    return HeldSaleListResponse(
        items=[
            serialize_held_sale(item)
            for item in held_sales
        ],
        total=total,
    )


@router.get(
    "/{held_sale_id}",
    response_model=HeldSaleResponse,
)
async def get_held_sale_endpoint(
    held_sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    held_sale = await get_held_sale(
        db,
        current_user.shop_id,
        held_sale_id,
    )

    return serialize_held_sale(held_sale)


@router.delete(
    "/{held_sale_id}",
    response_model=MessageResponse,
)
async def delete_held_sale_endpoint(
    held_sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    await delete_held_sale(
        db,
        current_user.shop_id,
        held_sale_id,
    )

    return MessageResponse(
        message="Held sale removed successfully."
    )
