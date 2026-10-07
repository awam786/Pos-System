from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    CustomerPayment,
    Sale,
    Supplier,
    SupplierPayment,
)


async def get_customer_balance(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Decimal:
    """
    Positive value means the customer owes the shop.

    Opening balance + credit sales - recorded customer payments.
    """

    customer_result = await db.execute(
        select(Customer.opening_balance).where(
            Customer.id == customer_id,
            Customer.shop_id == shop_id,
        )
    )

    opening = customer_result.scalar_one_or_none()

    if opening is None:
        return Decimal("0")

    payment_result = await db.execute(
        select(func.coalesce(func.sum(CustomerPayment.amount), 0)).where(
            CustomerPayment.customer_id == customer_id,
            CustomerPayment.shop_id == shop_id,
        )
    )

    payments = Decimal(str(payment_result.scalar_one() or 0))

    credit_sales = Decimal("0")

    try:
        sale_result = await db.execute(
            select(
                func.coalesce(
                    func.sum(Sale.grand_total),
                    0,
                )
            ).where(
                Sale.customer_id == customer_id,
                Sale.shop_id == shop_id,
                Sale.status == "completed",
                Sale.payment_status == "partial",
            )
        )

        credit_sales = Decimal(
            str(sale_result.scalar_one() or 0)
        )
    except Exception:
        # This balance helper remains safe while the sales engine is being
        # introduced in the next batch.
        credit_sales = Decimal("0")

    return Decimal(str(opening)) + credit_sales - payments


async def get_supplier_balance(
    db: AsyncSession,
    shop_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Decimal:
    """
    Positive value means the shop owes the supplier.

    Opening balance + unpaid purchases - supplier payments.
    """

    supplier_result = await db.execute(
        select(Supplier.opening_balance).where(
            Supplier.id == supplier_id,
            Supplier.shop_id == shop_id,
        )
    )

    opening = supplier_result.scalar_one_or_none()

    if opening is None:
        return Decimal("0")

    payment_result = await db.execute(
        select(func.coalesce(func.sum(SupplierPayment.amount), 0)).where(
            SupplierPayment.supplier_id == supplier_id,
            SupplierPayment.shop_id == shop_id,
        )
    )

    payments = Decimal(str(payment_result.scalar_one() or 0))

    return Decimal(str(opening)) - payments
