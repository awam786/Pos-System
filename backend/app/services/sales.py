from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CashMovement,
    Customer,
    Payment,
    Product,
    Sale,
    SaleItem,
    StockMovement,
)
from app.models.enums import CashMovementType, PaymentStatus, SaleStatus, StockMovementType
from app.schemas.sale import (
    SaleCalculationRequest,
    SaleCalculationResponse,
    SaleCreate,
    SaleItemResponse,
)
from app.services.inventory import get_open_cash_register


MONEY = Decimal("0.01")
QTY = Decimal("0.000001")


def money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")

    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def quantity(value: Decimal | int | float) -> Decimal:
    return Decimal(str(value)).quantize(QTY, rounding=ROUND_HALF_UP)


def calculate_discount(
    amount: Decimal,
    discount_type: str,
    discount_value: Decimal,
) -> Decimal:
    amount = money(amount)
    discount_value = money(discount_value)

    if discount_type == "none":
        return Decimal("0.00")

    if discount_type == "fixed":
        return min(amount, discount_value)

    if discount_type == "percentage":
        if discount_value > Decimal("100"):
            raise HTTPException(
                status_code=400,
                detail="Percentage discount cannot exceed 100%.",
            )

        return money(amount * discount_value / Decimal("100"))

    raise HTTPException(status_code=400, detail="Invalid discount type.")


def calculate_line(
    product: Product,
    item,
) -> tuple[Decimal, Decimal, Decimal]:
    unit_price = (
        money(item.unit_price)
        if item.unit_price is not None
        else money(product.selling_price)
    )

    if unit_price < 0:
        raise HTTPException(status_code=400, detail="Invalid product price.")

    qty = quantity(item.quantity)
    gross = money(unit_price * qty)

    discount = calculate_discount(
        gross,
        item.discount_type,
        item.discount_value,
    )

    line_total = money(gross - discount)

    return unit_price, discount, line_total


async def load_products(
    db: AsyncSession,
    shop_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, Product]:
    result = await db.execute(
        select(Product).where(
            Product.shop_id == shop_id,
            Product.id.in_(product_ids),
        )
    )

    products = {product.id: product for product in result.scalars().all()}

    if len(products) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="One or more products were not found.",
        )

    return products


async def calculate_sale(
    db: AsyncSession,
    shop_id: UUID,
    request: SaleCalculationRequest,
) -> SaleCalculationResponse:
    products = await load_products(
        db,
        shop_id,
        [item.product_id for item in request.items],
    )

    response_items: list[SaleItemResponse] = []
    subtotal = Decimal("0.00")
    item_discount_total = Decimal("0.00")

    for item in request.items:
        product = products[item.product_id]

        if not product.active:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product.name}' is inactive.",
            )

        unit_price, discount, line_total = calculate_line(product, item)

        subtotal += money(unit_price * quantity(item.quantity))
        item_discount_total += discount

        response_items.append(
            SaleItemResponse(
                id=UUID(int=0),
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                quantity=quantity(item.quantity),
                unit_price=unit_price,
                discount_type=item.discount_type,
                discount_value=money(item.discount_value),
                discount_amount=discount,
                line_total=line_total,
            )
        )

    subtotal = money(subtotal)

    bill_discount = calculate_discount(
        subtotal - item_discount_total,
        request.bill_discount_type,
        request.bill_discount_value,
    )

    grand_total = money(
        subtotal - item_discount_total - bill_discount
    )

    return SaleCalculationResponse(
        subtotal=subtotal,
        item_discount=item_discount_total,
        bill_discount=bill_discount,
        grand_total=grand_total,
        paid_amount=Decimal("0.00"),
        outstanding_amount=grand_total,
        change_amount=Decimal("0.00"),
        payment_status="unpaid",
        items=response_items,
    )


async def next_invoice_number(
    db: AsyncSession,
    shop_id: UUID,
) -> str:
    result = await db.execute(
        select(func.count(Sale.id)).where(
            Sale.shop_id == shop_id
        )
    )

    count = result.scalar_one() or 0

    return f"INV-{count + 1:08d}"


def determine_payment_status(
    total: Decimal,
    paid: Decimal,
) -> str:
    total = money(total)
    paid = money(paid)

    if paid >= total:
        return PaymentStatus.PAID

    if paid > 0:
        return PaymentStatus.PARTIAL

    return PaymentStatus.UNPAID


async def create_sale(
    db: AsyncSession,
    shop_id: UUID,
    user_id: UUID,
    request: SaleCreate,
) -> Sale:
    if not request.items:
        raise HTTPException(
            status_code=400,
            detail="A sale must contain at least one item.",
        )

    product_ids = [item.product_id for item in request.items]
    products = await load_products(db, shop_id, product_ids)

    customer = None

    if request.customer_id:
        customer = await db.scalar(
            select(Customer).where(
                Customer.id == request.customer_id,
                Customer.shop_id == shop_id,
            )
        )

        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

    calculated_items = []

    subtotal = Decimal("0.00")
    item_discount_total = Decimal("0.00")

    for item in request.items:
        product = products[item.product_id]

        if not product.active:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product.name}' is inactive.",
            )

        requested_quantity = quantity(item.quantity)

        if requested_quantity > quantity(product.current_stock):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient stock for '{product.name}'. "
                    f"Available: {product.current_stock}."
                ),
            )

        unit_price, discount, line_total = calculate_line(
            product,
            item,
        )

        subtotal += money(unit_price * requested_quantity)
        item_discount_total += discount

        calculated_items.append(
            (
                item,
                product,
                requested_quantity,
                unit_price,
                discount,
                line_total,
            )
        )

    subtotal = money(subtotal)

    bill_discount = calculate_discount(
        subtotal - item_discount_total,
        request.bill_discount_type,
        request.bill_discount_value,
    )

    grand_total = money(
        subtotal - item_discount_total - bill_discount
    )

    supplied_payment_total = money(
        sum(
            (money(payment.amount) for payment in request.payments),
            Decimal("0.00"),
        )
    )

    cash_received = money(request.cash_received)

    has_cash_payment = any(
        payment.method == "cash"
        for payment in request.payments
    )

    if has_cash_payment and request.cash_received is not None:
        if cash_received <= 0:
            raise HTTPException(
                status_code=400,
                detail="Cash received must be greater than zero.",
            )

        if cash_received < supplied_payment_total:
            raise HTTPException(
                status_code=400,
                detail="Cash received cannot be less than the cash payment.",
            )

    if supplied_payment_total > grand_total:
        raise HTTPException(
            status_code=400,
            detail="Payment total cannot exceed the sale total.",
        )

    outstanding = money(grand_total - supplied_payment_total)

    if outstanding > 0 and customer is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Customer is required when the sale is not fully paid."
            ),
        )

    if customer and customer.credit_limit > 0:
        if outstanding > money(customer.credit_limit):
            raise HTTPException(
                status_code=400,
                detail="Customer credit limit would be exceeded.",
            )

    change_amount = Decimal("0.00")

    if has_cash_payment and request.cash_received is not None:
        cash_payment_amount = money(
            sum(
                (
                    money(payment.amount)
                    for payment in request.payments
                    if payment.method == "cash"
                ),
                Decimal("0.00"),
            )
        )

        if cash_received > cash_payment_amount:
            change_amount = money(
                cash_received - cash_payment_amount
            )

    invoice_number = await next_invoice_number(db, shop_id)

    sale = Sale(
        shop_id=shop_id,
        customer_id=request.customer_id,
        user_id=user_id,
        invoice_number=invoice_number,
        subtotal=subtotal,
        discount_type=request.bill_discount_type,
        discount_value=money(request.bill_discount_value),
        discount_amount=money(
            item_discount_total + bill_discount
        ),
        grand_total=grand_total,
        paid_amount=supplied_payment_total,
        change_amount=change_amount,
        payment_status=determine_payment_status(
            grand_total,
            supplied_payment_total,
        ),
        status=SaleStatus.COMPLETED,
        notes=request.notes,
    )

    db.add(sale)
    await db.flush()

    for (
        item,
        product,
        requested_quantity,
        unit_price,
        discount,
        line_total,
    ) in calculated_items:
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            quantity=requested_quantity,
            unit_price=unit_price,
            discount_type=item.discount_type,
            discount_value=money(item.discount_value),
            discount_amount=discount,
            line_total=line_total,
        )

        db.add(sale_item)

        product.current_stock = (
            quantity(product.current_stock)
            - requested_quantity
        )

        db.add(
            StockMovement(
                shop_id=shop_id,
                product_id=product.id,
                user_id=user_id,
                movement_type=StockMovementType.SALE,
                quantity=-requested_quantity,
                reference=invoice_number,
                notes=f"Sale {invoice_number}",
            )
        )

    for payment in request.payments:
        amount = money(payment.amount)

        db.add(
            Payment(
                sale_id=sale.id,
                method=payment.method,
                amount=amount,
                reference=payment.reference,
                notes=payment.notes,
            )
        )

        if payment.method == "cash":
            register = await get_open_cash_register(
                db,
                shop_id,
            )

            if not register:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Open the cash register before accepting "
                        "cash payments."
                    ),
                )

            db.add(
                CashMovement(
                    cash_register_id=register.id,
                    user_id=user_id,
                    movement_type=CashMovementType.SALE,
                    amount=amount,
                    reference=invoice_number,
                    notes=f"Cash payment for {invoice_number}",
                )
            )

    await db.commit()

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
            status_code=404,
            detail="Sale not found.",
        )

    return sale


async def list_sales(
    db: AsyncSession,
    shop_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Sale], int]:
    count_result = await db.execute(
        select(func.count(Sale.id)).where(
            Sale.shop_id == shop_id
        )
    )

    total = count_result.scalar_one() or 0

    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.items),
            selectinload(Sale.payments),
        )
        .where(Sale.shop_id == shop_id)
        .order_by(Sale.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(result.scalars().all()), total
