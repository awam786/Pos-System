from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Sale
from app.schemas.payment import PaymentCreate


async def get_sale_payment_total(
    db: AsyncSession,
    sale_id: UUID,
) -> Decimal:
    result = await db.execute(
        select(Payment.amount).where(
            Payment.sale_id == sale_id
        )
    )

    return sum(
        (Decimal(str(value)) for value in result.scalars().all()),
        Decimal("0.00"),
    )


async def add_payment(
    db: AsyncSession,
    shop_id: UUID,
    sale_id: UUID,
    request: PaymentCreate,
) -> Payment:
    sale = await db.scalar(
        select(Sale).where(
            Sale.id == sale_id,
            Sale.shop_id == shop_id,
        )
    )

    if not sale:
        raise HTTPException(
            status_code=404,
            detail="Sale not found.",
        )

    if sale.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Payments can only be added to completed sales.",
        )

    current_paid = await get_sale_payment_total(
        db,
        sale_id,
    )

    remaining = Decimal(str(sale.grand_total)) - current_paid

    if request.amount > remaining:
        raise HTTPException(
            status_code=400,
            detail="Payment exceeds the outstanding balance.",
        )

    payment = Payment(
        sale_id=sale_id,
        method=request.method,
        amount=request.amount,
        reference=request.reference,
        notes=request.notes,
    )

    db.add(payment)

    new_paid = current_paid + request.amount

    sale.paid_amount = new_paid

    if new_paid >= sale.grand_total:
        sale.payment_status = "paid"
    elif new_paid > 0:
        sale.payment_status = "partial"
    else:
        sale.payment_status = "unpaid"

    await db.commit()
    await db.refresh(payment)

    return payment
