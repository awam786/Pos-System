from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.models.user import User
from app.permissions import Permission
from app.schemas.common import MessageResponse
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.schemas.sale import (
    SaleCalculationRequest,
    SaleCalculationResponse,
    SaleCreate,
    SaleItemResponse,
    SaleListResponse,
    SalePaymentResponse,
    SaleResponse,
)
from app.services.payments import add_payment
from app.services.permissions import require_permission
from app.services.sales import (
    calculate_sale,
    create_sale,
    get_sale,
    list_sales,
)


router = APIRouter(
    prefix="/sales",
    tags=["Sales"],
)


def serialize_sale(sale) -> SaleResponse:
    items = [
        SaleItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_type=item.discount_type,
            discount_value=item.discount_value,
            discount_amount=item.discount_amount,
            line_total=item.line_total,
        )
        for item in sale.items
    ]

    payments = [
        SalePaymentResponse(
            id=payment.id,
            method=payment.method,
            amount=payment.amount,
            reference=payment.reference,
            notes=payment.notes,
        )
        for payment in sale.payments
    ]

    return SaleResponse(
        id=sale.id,
        invoice_number=sale.invoice_number,
        customer_id=sale.customer_id,
        user_id=sale.user_id,
        subtotal=sale.subtotal,
        discount_type=sale.discount_type,
        discount_value=sale.discount_value,
        discount_amount=sale.discount_amount,
        grand_total=sale.grand_total,
        paid_amount=sale.paid_amount,
        change_amount=sale.change_amount,
        payment_status=sale.payment_status,
        status=sale.status,
        notes=sale.notes,
        items=items,
        payments=payments,
    )


@router.post(
    "/calculate",
    response_model=SaleCalculationResponse,
)
async def calculate_sale_endpoint(
    payload: SaleCalculationRequest,
    db: AsyncSession = Depends(__import__(
        "app.database",
        fromlist=["get_db"],
    ).get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    return await calculate_sale(
        db,
        current_user.shop_id,
        payload,
    )


@router.post(
    "",
    response_model=SaleResponse,
)
async def create_sale_endpoint(
    payload: SaleCreate,
    db: AsyncSession = Depends(__import__(
        "app.database",
        fromlist=["get_db"],
    ).get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

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
async def list_sales_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(__import__(
        "app.database",
        fromlist=["get_db"],
    ).get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    sales, total = await list_sales(
        db,
        current_user.shop_id,
        limit,
        offset,
    )

    return SaleListResponse(
        items=[serialize_sale(sale) for sale in sales],
        total=total,
    )


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
)
async def get_sale_endpoint(
    sale_id: UUID,
    db: AsyncSession = Depends(__import__(
        "app.database",
        fromlist=["get_db"],
    ).get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    sale = await get_sale(
        db,
        current_user.shop_id,
        sale_id,
    )

    return serialize_sale(sale)


@router.post(
    "/{sale_id}/payments",
    response_model=PaymentResponse,
)
async def add_payment_endpoint(
    sale_id: UUID,
    payload: PaymentCreate,
    db: AsyncSession = Depends(__import__(
        "app.database",
        fromlist=["get_db"],
    ).get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.SALES,
    )

    payment = await add_payment(
        db,
        current_user.shop_id,
        sale_id,
        payload,
    )

    return PaymentResponse(
        id=payment.id,
        sale_id=payment.sale_id,
        method=payment.method,
        amount=payment.amount,
        reference=payment.reference,
        notes=payment.notes,
    )


@router.post(
    "/{sale_id}/void",
    response_model=MessageResponse,
)
async def void_sale_endpoint(
    sale_id: UUID,
    db: AsyncSession = Depends(__import__(
        "app.database",
        fromlist=["get_db"],
    ).get_db),
    current_user: User = Depends(get_current_user),
):
    await require_permission(
        current_user,
        Permission.RETURNS,
    )

    sale = await get_sale(
        db,
        current_user.shop_id,
        sale_id,
    )

    if sale.status == "void":
        return MessageResponse(
            message="Sale is already voided."
        )

    sale.status = "void"

    await db.commit()

    return MessageResponse(
        message=f"Sale {sale.invoice_number} has been voided."
    )
