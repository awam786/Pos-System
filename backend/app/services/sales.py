from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import CashMovementType, SaleStatus, StockMovementType
from app.models.inventory import CashMovement, CashRegister, StockMovement
from app.models.partner import Customer
from app.models.product import Product, ProductCode
from app.models.transaction import Payment, Sale, SaleItem
from app.schemas.sale import (
    SaleCalculationRequest,
    SaleCreate,
)


CENT = Decimal("0.01")
QTY = Decimal("0.001")


def money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def quantity(value: Decimal | int | float) -> Decimal:
    return Decimal(str(value)).quantize(
        QTY,
        rounding=ROUND_HALF_UP,
    )


async def get_product(
    db: AsyncSession,
    shop_id: UUID,
    product_id: UUID,
) -> Product:
    product = await db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.shop_id == shop_id,
        )
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is archived.",
        )

    return product


async def next_receipt_number(
    db: AsyncSession,
    shop_id: UUID,
) -> str:
    result = await db.execute(
        select(func.count(Sale.id)).where(
            Sale.shop_id == shop_id
        )
    )

    count = int(result.scalar() or 0)

    return f"INV-{count + 1:08d}"


async def calculate_sale(
    db: AsyncSession,
    shop_id: UUID,
    payload: SaleCalculationRequest,
) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = Decimal("0.00")
    item_discounts = Decimal("0.00")

    for item in payload.items:
        product = await get_product(
            db,
            shop_id,
            item.product_id,
        )

        unit_price = (
            money(item.unit_price)
            if item.unit_price is not None
            else money(product.selling_price)
        )

        qty = quantity(item.quantity)
        discount = money(item.discount)

        line_subtotal = money(unit_price * qty)

        if discount > line_subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Discount exceeds line total for {product.name}.",
            )

        subtotal += line_subtotal
        item_discounts += discount

    bill_discount = money(payload.discount)
    available = money(subtotal - item_discounts)

    if bill_discount > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill discount exceeds the sale amount.",
        )

    total_discount = money(item_discounts + bill_discount)
    total = money(subtotal - total_discount)

    return money(subtotal), total_discount, total


async def create_sale(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID,
    payload: SaleCreate,
) -> Sale:
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A sale must contain at least one item.",
        )

    customer = None

    if payload.customer_id:
        customer = await db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.shop_id == shop_id,
                Customer.active.is_(True),
            )
        )

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

    subtotal = Decimal("0.00")
    item_discount_total = Decimal("0.00")
    prepared_items = []

    for requested in payload.items:
        product = await get_product(
            db,
            shop_id,
            requested.product_id,
        )

        qty = quantity(requested.quantity)

        if product.stock_quantity < qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock for {product.name}. "
                    f"Available: {product.stock_quantity}."
                ),
            )

        unit_price = (
            money(requested.unit_price)
            if requested.unit_price is not None
            else money(product.selling_price)
        )

        line_discount = money(requested.discount)
        line_subtotal = money(unit_price * qty)

        if line_discount > line_subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Discount exceeds line total for {product.name}.",
            )

        line_total = money(line_subtotal - line_discount)

        subtotal += line_subtotal
        item_discount_total += line_discount

        prepared_items.append(
            (
                product,
                qty,
                unit_price,
                line_discount,
                line_total,
            )
        )

    bill_discount = money(payload.discount)
    amount_before_bill_discount = money(
        subtotal - item_discount_total
    )

    if bill_discount > amount_before_bill_discount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill discount exceeds the remaining sale amount.",
        )

    total_discount = money(
        item_discount_total + bill_discount
    )

    total = money(subtotal - total_discount)

    payment_total = Decimal("0.00")
    cash_received_total = Decimal("0.00")
    cash_change_total = Decimal("0.00")

    for payment in payload.payments:
        amount = money(payment.amount)

        if payment.method == "cash":
            received = money(
                payment.received_amount
                if payment.received_amount is not None
                else amount
            )

            if received < amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cash received cannot be less than the payment amount.",
                )

            change = money(received - amount)

            cash_received_total += received
            cash_change_total += change

        payment_total += amount

    if payment_total > total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount cannot exceed the sale total.",
        )

    credit_amount = money(total - payment_total)

    if credit_amount > 0 and not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer is required for credit sales.",
        )

    if customer and customer.credit_limit > 0:
        existing_balance_result = await db.execute(
            select(
                func.coalesce(
                    func.sum(Sale.credit_amount),
                    Decimal("0.00"),
                )
            ).where(
                Sale.shop_id == shop_id,
                Sale.customer_id == customer.id,
            )
        )

        existing_credit = money(
            existing_balance_result.scalar() or 0
        )

        payment_result = await db.execute(
            select(
                func.coalesce(
                    func.sum(
                        db.bindparam("zero")
                        if False
                        else Customer.id
                    ),
                    0,
                )
            ).where(Customer.id == customer.id)
        )

        del payment_result

        from app.models.partner import CustomerPayment

        paid_result = await db.execute(
            select(
                func.coalesce(
                    func.sum(CustomerPayment.amount),
                    Decimal("0.00"),
                )
            ).where(
                CustomerPayment.shop_id == shop_id,
                CustomerPayment.customer_id == customer.id,
            )
        )

        existing_payments = money(
            paid_result.scalar() or 0
        )

        existing_balance = max(
            existing_credit
            + money(customer.opening_balance)
            - existing_payments,
            Decimal("0.00"),
        )

        if existing_balance + credit_amount > customer.credit_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer credit limit would be exceeded.",
            )

    cash_register = None

    if any(payment.method == "cash" for payment in payload.payments):
        cash_register = await db.scalar(
            select(CashRegister)
            .where(
                CashRegister.shop_id == shop_id,
                CashRegister.is_open.is_(True),
            )
            .order_by(CashRegister.created_at.desc())
            .limit(1)
        )

        if not cash_register:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Open a cash register before accepting cash.",
            )

    receipt_number = await next_receipt_number(
        db,
        shop_id,
    )

    sale = Sale(
        shop_id=shop_id,
        customer_id=customer.id if customer else None,
        user_id=user_id,
        cash_register_id=(
            cash_register.id if cash_register else None
        ),
        receipt_number=receipt_number,
        status=SaleStatus.COMPLETED.value,
        subtotal=money(subtotal),
        discount=total_discount,
        total=total,
        paid_amount=payment_total,
        credit_amount=credit_amount,
        notes=payload.notes.strip()
        if payload.notes
        else None,
    )

    db.add(sale)
    await db.flush()

    for (
        product,
        qty,
        unit_price,
        line_discount,
        line_total,
    ) in prepared_items:
        product.stock_quantity -= qty

        code_result = await db.execute(
            select(ProductCode.code)
            .where(
                ProductCode.product_id == product.id,
                ProductCode.shop_id == shop_id,
            )
            .order_by(ProductCode.created_at.asc())
            .limit(1)
        )

        product_code = code_result.scalar_one_or_none()

        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                product_code=product_code,
                quantity=qty,
                unit_price=unit_price,
                discount=line_discount,
                total=line_total,
            )
        )

        db.add(
            StockMovement(
                shop_id=shop_id,
                product_id=product.id,
                user_id=user_id,
                movement_type=StockMovementType.SALE.value,
                quantity=-qty,
                balance_after=product.stock_quantity,
                reference_type="sale",
                reference_id=sale.id,
                notes=f"Sale {receipt_number}",
            )
        )

    for payment in payload.payments:
        amount = money(payment.amount)

        received = (
            money(payment.received_amount)
            if payment.received_amount is not None
            else amount
        )

        change = (
            money(received - amount)
            if payment.method == "cash"
            else Decimal("0.00")
        )

        db.add(
            Payment(
                sale_id=sale.id,
                method=payment.method,
                amount=amount,
                received_amount=received,
                change_amount=change,
                reference=payment.reference,
                notes=payment.notes,
            )
        )

        if payment.method == "cash" and cash_register:
            db.add(
                CashMovement(
                    cash_register_id=cash_register.id,
                    user_id=user_id,
                    movement_type=CashMovementType.SALE.value,
                    amount=amount,
                    reference_id=sale.id,
                    description=f"Cash sale {receipt_number}",
                )
            )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(sale)

    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.items),
            selectinload(Sale.payments),
        )
        .where(
            Sale.id == sale.id,
            Sale.shop_id == shop_id,
        )
    )

    return result.scalar_one()


async def get_sale(
    db: AsyncSession,
    shop_id: UUID,
    sale_id: UUID,
) -> Sale:
    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.items),
            selectinload(Sale.payments),
        )
        .where(
            Sale.id == sale_id,
            Sale.shop_id == shop_id,
        )
    )

    sale = result.scalar_one_or_none()

    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found.",
        )

    return sale


async def list_sales(
    db: AsyncSession,
    shop_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Sale], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    total_result = await db.execute(
        select(func.count(Sale.id)).where(
            Sale.shop_id == shop_id
        )
    )

    total = int(total_result.scalar() or 0)

    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.items),
            selectinload(Sale.payments),
        )
        .where(Sale.shop_id == shop_id)
        .order_by(Sale.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return list(result.scalars().all()), total
