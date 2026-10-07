from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, get_current_user
from app.models.user import User
from app.permissions import Permission
from app.schemas.sale import (
    SaleCalculationRequest,
    SaleCalculationResponse,
    SaleCreate,
    SaleListResponse,
    SaleResponse,
)
from app.services.permissions import require_permission
from app.services.sales import (
    calculate_sale,
    create_sale,
    get_sale,
    list_sales,
)


router = APIRouter(prefix="/sales", tags=["Sales"])


def serialize_sale(sale) -> SaleResponse:
    return SaleResponse(
        id=sale.id,
        receipt_number=sale.receipt_number,
        customer_id=sale.customer_id,
        subtotal=sale.subtotal,
        discount=sale.discount,
        total=sale.total,
        paid_amount=sale.paid_amount,
        credit_amount=sale.credit_amount,
        status=str(sale.status),
        notes=sale.notes,
        created_at=sale.created_at,
        items=sale.items,
        payments=sale.payments,
    )


@router.post(
    "/calculate",
    response_model=SaleCalculationResponse,
)
async def calculate(
    payload: SaleCalculationRequest,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    subtotal, discount, total = await calculate_sale(
        db,
        current_user.shop_id,
        payload,
    )

    return SaleCalculationResponse(
        subtotal=subtotal,
        discount=discount,
        total=total,
    )


@router.post(
    "",
    response_model=SaleResponse,
    status_code=201,
)
async def create(
    payload: SaleCreate,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    sale = await create_sale(
        db,
        current_user.shop_id,
        current_user.id,
        payload,
    )

    return serialize_sale(sale)


@router.get(
    "",
    response_model=SaleListResponse,
)
async def list_all(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    sales, total = await list_sales(
        db,
        current_user.shop_id,
        page,
        page_size,
    )

    return SaleListResponse(
        items=[serialize_sale(sale) for sale in sales],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
)
async def get(
    sale_id: UUID,
    db: AsyncSession = Depends(DbSession),
    current_user: User = Depends(get_current_user),
):
    require_permission(current_user, Permission.SALES)

    sale = await get_sale(
        db,
        current_user.shop_id,
        sale_id,
    )

    return serialize_sale(sale)
