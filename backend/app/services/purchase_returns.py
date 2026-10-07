from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    CashMovementType,
    ReturnStatus,
    SaleStatus,
    StockMovementType,
)
from app.models.inventory import CashMovement, CashRegister, StockMovement
from app.models.partner import Supplier, SupplierPayment
from app.models.product import Product
from app.models.transaction import (
    Purchase,
    PurchaseItem,
    Return,
    ReturnItem,
    Sale,
    SaleItem,
)
from app.schemas.purchase_return import (
    PurchaseCreate,
    ReturnCreate,
)


CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


async def create_purchase(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID,
    payload: PurchaseCreate,
) -> Purchase:
    supplier = None

    if payload.supplier_id:
        supplier = await db.scalar(
            select(Supplier).where(
                Supplier.id == payload.supplier_id,
                Supplier.shop_id == shop_id,
                Supplier.active.is_(True),
            )
        )

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found.",
            )

    payment_method = payload.payment_method.strip().lower()

    if payment_method not in {
        "cash",
        "bank",
        "card",
        "other",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid purchase payment method.",
        )

    subtotal = Decimal("0.00")
    prepared = []

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
                status_code=404,
                detail="One or more products were not found.",
            )

        quantity = Decimal(str(item.quantity))
        unit_cost = money(item.unit_cost)
        discount = money(item.discount)

        line_subtotal = money(quantity * unit_cost)

        if discount > line_subtotal:
            raise HTTPException(
                status_code=400,
                detail=f"Discount exceeds purchase line for {product.name}.",
            )

        line_total = money(line_subtotal - discount)

        subtotal += line_subtotal

        prepared.append(
            (
                product,
                quantity,
                unit_cost,
                discount,
                line_total,
            )
        )

    purchase_discount = money(payload.discount)

    if purchase_discount > subtotal:
        raise HTTPException(
            status_code=400,
            detail="Purchase discount exceeds subtotal.",
        )

    total = money(subtotal - purchase_discount)
    paid_amount = money(payload.paid_amount)

    if paid_amount > total:
        raise HTTPException(
            status_code=400,
            detail="Paid amount cannot exceed purchase total.",
        )

    purchase = Purchase(
        shop_id=shop_id,
        supplier_id=supplier.id if supplier else None,
        user_id=user_id,
        invoice_number=payload.invoice_number,
        status="received",
        subtotal=subtotal,
        discount=purchase_discount,
        total=total,
        paid_amount=paid_amount,
        notes=payload.notes,
    )

    db.add(purchase)
    await db.flush()

    for (
        product,
        quantity,
        unit_cost,
        discount,
        line_total,
    ) in prepared:
        product.stock_quantity += quantity

        db.add(
            PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=quantity,
                unit_cost=unit_cost,
                discount=discount,
                total=line_total,
            )
        )

        db.add(
            StockMovement(
                shop_id=shop_id,
                product_id=product.id,
                user_id=user_id,
                movement_type=StockMovementType.PURCHASE.value,
                quantity=quantity,
                balance_after=product.stock_quantity,
                reference_type="purchase",
                reference_id=purchase.id,
                notes=(
                    f"Purchase "
                    f"{payload.invoice_number or purchase.id}"
                ),
            )
        )

    if supplier and paid_amount > 0:
        db.add(
            SupplierPayment(
                shop_id=shop_id,
                supplier_id=supplier.id,
                user_id=user_id,
                amount=paid_amount,
                payment_method=payment_method,
                reference=payload.payment_reference,
                notes=f"Payment for purchase {purchase.id}",
            )
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(purchase)

    result = await db.execute(
        select(Purchase)
        .options(selectinload(Purchase.items))
        .where(
            Purchase.id == purchase.id,
            Purchase.shop_id == shop_id,
        )
    )

    return result.scalar_one()


async def get_purchase(
    db: AsyncSession,
    shop_id: UUID,
    purchase_id: UUID,
) -> Purchase:
    result = await db.execute(
        select(Purchase)
        .options(selectinload(Purchase.items))
        .where(
            Purchase.id == purchase_id,
            Purchase.shop_id == shop_id,
        )
    )

    purchase = result.scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found.",
        )

    return purchase


async def list_purchases(
    db: AsyncSession,
    shop_id: UUID,
) -> list[Purchase]:
    result = await db.execute(
        select(Purchase)
        .options(selectinload(Purchase.items))
        .where(Purchase.shop_id == shop_id)
        .order_by(Purchase.created_at.desc())
    )

    return list(result.scalars().all())


async def create_return(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID,
    payload: ReturnCreate,
) -> Return:
    sale = await db.scalar(
        select(Sale)
        .options(selectinload(Sale.items))
        .where(
            Sale.id == payload.sale_id,
            Sale.shop_id == shop_id,
        )
    )

    if not sale:
        raise HTTPException(
            status_code=404,
            detail="Sale not found.",
        )

    if sale.status == SaleStatus.VOIDED.value:
        raise HTTPException(
            status_code=400,
            detail="Voided sales cannot be returned.",
        )

    sale_items = {
        item.id: item
        for item in sale.items
    }

    returned_result = await db.execute(
        select(ReturnItem)
        .join(Return)
        .where(
            Return.shop_id == shop_id,
            Return.sale_id == sale.id,
            Return.status != "cancelled",
        )
    )

    returned_by_item: dict[UUID, Decimal] = {}

    for item in returned_result.scalars().all():
        returned_by_item[item.sale_item_id] = (
            returned_by_item.get(item.sale_item_id, Decimal("0"))
            + item.quantity
        )

    return_total = Decimal("0.00")

    return_record = Return(
        shop_id=shop_id,
        sale_id=sale.id,
        user_id=user_id,
        status=ReturnStatus.COMPLETED.value,
        total=Decimal("0.00"),
        refund_amount=money(payload.refund_amount),
        reason=payload.reason,
    )

    db.add(return_record)
    await db.flush()

    for requested in payload.items:
        sale_item = sale_items.get(requested.sale_item_id)

        if not sale_item:
            raise HTTPException(
                status_code=400,
                detail="Sale item does not belong to this sale.",
            )

        already_returned = returned_by_item.get(
            sale_item.id,
            Decimal("0"),
        )

        available = sale_item.quantity - already_returned
        requested_quantity = Decimal(str(requested.quantity))

        if requested_quantity > available:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot return {requested_quantity} units of "
                    f"{sale_item.product_name}. "
                    f"Only {available} remain returnable."
                ),
            )

        unit_value = (
            sale_item.total / sale_item.quantity
            if sale_item.quantity
            else Decimal("0")
        )

        amount = money(unit_value * requested_quantity)

        product = await db.scalar(
            select(Product).where(
                Product.id == sale_item.product_id,
                Product.shop_id == shop_id,
            )
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product no longer exists.",
            )

        product.stock_quantity += requested_quantity

        return_total += amount

        db.add(
            ReturnItem(
                return_id=return_record.id,
                sale_item_id=sale_item.id,
                product_id=product.id,
                quantity=requested_quantity,
                amount=amount,
            )
        )

        db.add(
            StockMovement(
                shop_id=shop_id,
                product_id=product.id,
                user_id=user_id,
                movement_type=StockMovementType.RETURN.value,
                quantity=requested_quantity,
                balance_after=product.stock_quantity,
                reference_type="return",
                reference_id=return_record.id,
                notes=f"Return for sale {sale.receipt_number}",
            )
        )

    return_record.total = money(return_total)

    if return_record.refund_amount > return_record.total:
        raise HTTPException(
            status_code=400,
            detail="Refund amount cannot exceed return amount.",
        )

    cumulative_result = await db.execute(
        select(
            func.coalesce(
                func.sum(Return.total),
                Decimal("0.00"),
            )
        ).where(
            Return.sale_id == sale.id,
            Return.shop_id == shop_id,
            Return.id != return_record.id,
            Return.status != "cancelled",
        )
    )

    previous_returns = money(
        cumulative_result.scalar() or 0
    )

    cumulative_returns = money(
        previous_returns + return_record.total
    )

    if cumulative_returns >= sale.total:
        sale.status = SaleStatus.RETURNED.value
    else:
        sale.status = SaleStatus.PARTIAL_RETURN.value

    refund_amount = money(
        return_record.refund_amount
    )

    if refund_amount > 0:
        register = await db.scalar(
            select(CashRegister)
            .where(
                CashRegister.shop_id == shop_id,
                CashRegister.is_open.is_(True),
            )
            .order_by(CashRegister.created_at.desc())
            .limit(1)
        )

        if not register:
            raise HTTPException(
                status_code=400,
                detail=(
                    "An open cash register is required "
                    "to issue a cash refund."
                ),
            )

        db.add(
            CashMovement(
                cash_register_id=register.id,
                user_id=user_id,
                movement_type=CashMovementType.REFUND.value,
                amount=refund_amount,
                reference_id=return_record.id,
                description=(
                    f"Refund for sale {sale.receipt_number}"
                ),
            )
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(return_record)

    result = await db.execute(
        select(Return)
        .options(selectinload(Return.items))
        .where(
            Return.id == return_record.id,
            Return.shop_id == shop_id,
        )
    )

    return result.scalar_one()


async def get_return(
    db: AsyncSession,
    shop_id: UUID,
    return_id: UUID,
) -> Return:
    result = await db.execute(
        select(Return)
        .options(selectinload(Return.items))
        .where(
            Return.id == return_id,
            Return.shop_id == shop_id,
        )
    )

    return_record = result.scalar_one_or_none()

    if not return_record:
        raise HTTPException(
            status_code=404,
            detail="Return not found.",
        )

    return return_record
