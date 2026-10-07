from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, get_current_user
from app.models.user import User
from app.permissions import Permission
from app.schemas.purchase_return import (
    PurchaseCreate,
    PurchaseItemResponse,
    PurchaseResponse,
    ReturnCreate,
    ReturnItemResponse,
    ReturnResponse,
)
from app.services.permissions import require_permission
from app.services.purchases_returns import (
    create_purchase,
    create_return,
    get_purchase,
    get_return,
    list_purchases,
)


router = APIRouter(
    prefix="",
    tags=["Purchases & Returns"],
)


def serialize_purchase(purchase) -> PurchaseResponse:
    return PurchaseResponse(
        id=purchase.id,
        supplier_id=purchase.supplier_id,
        invoice_number=purchase.invoice_number,
        status=str(purchase.status),
        subtotal=purchase.subtotal,
        discount=purchase.discount,
        total=purchase.total,
        paid_amount=purchase.paid_amount,
        notes=purchase.notes,
        created_at=purchase.created_at,
        items=[
            PurchaseItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                discount=item.discount,
                total=item.total,
            )
            for item in purchase.items
        ],
    )


def serialize_return(return_record) -> ReturnResponse:
    return ReturnResponse(
        id=return_record.id,
        sale_id=return_record.sale_id,
        status=str(return_record.status),
        total=return_record.total,
        refund_amount=return_record.refund_amount,
        reason=return_record.reason,
        created_at=return_record.created_at,
        items=[
            ReturnItemResponse(
                id=item.id,
                sale_item_id=item.sale_item_id,
                product_id=item.product_id,
                quantity=item.quantity,
                amount=item.amount,
            )
            for item in return_record.items
        ],
    )


@router.post(
    "/purchases",
    response_model=PurchaseResponse,
    status_code=201,
)
async def create_purchase_endpoint(
    payload: PurchaseCreate,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.PURCHASES)

    purchase = await create_purchase(
        db,
        current_user.shop_id,
        current_user.id,
        payload,
    )

    return serialize_purchase(purchase)


@router.get(
    "/purchases",
    response_model=list[PurchaseResponse],
)
async def list_purchase_endpoint(
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.PURCHASES)

    purchases = await list_purchases(
        db,
        current_user.shop_id,
    )

    return [
        serialize_purchase(purchase)
        for purchase in purchases
    ]


@router.get(
    "/purchases/{purchase_id}",
    response_model=PurchaseResponse,
)
async def get_purchase_endpoint(
    purchase_id: UUID,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.PURCHASES)

    purchase = await get_purchase(
        db,
        current_user.shop_id,
        purchase_id,
    )

    return serialize_purchase(purchase)


@router.post(
    "/returns",
    response_model=ReturnResponse,
    status_code=201,
)
async def create_return_endpoint(
    payload: ReturnCreate,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.RETURNS)

    return_record = await create_return(
        db,
        current_user.shop_id,
        current_user.id,
        payload,
    )

    return serialize_return(return_record)


@router.get(
    "/returns/{return_id}",
    response_model=ReturnResponse,
)
async def get_return_endpoint(
    return_id: UUID,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.RETURNS)

    return_record = await get_return(
        db,
        current_user.shop_id,
        return_id,
    )

    return serialize_return(return_record)
