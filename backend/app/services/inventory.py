from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CashMovement,
    CashMovementType,
    CashRegister,
    Expense,
    Product,
    StockMovement,
    StockMovementType,
)


async def get_product(
    db: AsyncSession,
    shop_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.shop_id == shop_id,
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


async def adjust_stock(
    db: AsyncSession,
    shop_id: uuid.UUID,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: Decimal,
    notes: str | None = None,
) -> StockMovement:
    product = await get_product(
        db,
        shop_id,
        product_id,
    )

    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot adjust stock for an archived product.",
        )

    new_balance = product.stock_quantity + quantity

    if new_balance < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock. Current stock is "
                f"{product.stock_quantity}."
            ),
        )

    movement_type = (
        StockMovementType.ADJUSTMENT_IN.value
        if quantity > 0
        else StockMovementType.ADJUSTMENT_OUT.value
    )

    product.stock_quantity = new_balance

    movement = StockMovement(
        shop_id=shop_id,
        product_id=product.id,
        user_id=user_id,
        movement_type=movement_type,
        quantity=quantity,
        balance_after=new_balance,
        reference_type="manual_adjustment",
        notes=notes.strip() if notes else None,
    )

    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    return movement


async def record_stock_movement(
    db: AsyncSession,
    shop_id: uuid.UUID,
    user_id: uuid.UUID | None,
    product: Product,
    quantity: Decimal,
    movement_type: str,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> StockMovement:
    new_balance = product.stock_quantity + quantity

    if new_balance < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock for {product.name}. "
                f"Available: {product.stock_quantity}."
            ),
        )

    product.stock_quantity = new_balance

    movement = StockMovement(
        shop_id=shop_id,
        product_id=product.id,
        user_id=user_id,
        movement_type=movement_type,
        quantity=quantity,
        balance_after=new_balance,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
    )

    db.add(movement)

    return movement


async def create_expense(
    db: AsyncSession,
    shop_id: uuid.UUID,
    user_id: uuid.UUID,
    category: str,
    amount: Decimal,
    payment_method: str,
    description: str | None,
    reference: str | None,
) -> Expense:
    expense = Expense(
        shop_id=shop_id,
        user_id=user_id,
        category=category,
        amount=amount,
        payment_method=payment_method,
        description=description,
        reference=reference,
    )

    db.add(expense)
    await db.commit()
    await db.refresh(expense)

    return expense


async def get_open_cash_register(
    db: AsyncSession,
    shop_id: uuid.UUID,
) -> CashRegister | None:
    result = await db.execute(
        select(CashRegister)
        .where(
            CashRegister.shop_id == shop_id,
            CashRegister.is_open.is_(True),
        )
        .order_by(CashRegister.created_at.desc())
        .limit(1)
    )

    return result.scalar_one_or_none()


async def open_cash_register(
    db: AsyncSession,
    shop_id: uuid.UUID,
    user_id: uuid.UUID,
    opening_balance: Decimal,
    notes: str | None = None,
) -> CashRegister:
    existing = await get_open_cash_register(
        db,
        shop_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A cash register is already open.",
        )

    register = CashRegister(
        shop_id=shop_id,
        opened_by=user_id,
        opening_balance=opening_balance,
        is_open=True,
        notes=notes.strip() if notes else None,
    )

    db.add(register)
    await db.flush()

    if opening_balance > 0:
        db.add(
            CashMovement(
                cash_register_id=register.id,
                user_id=user_id,
                movement_type=CashMovementType.OPENING.value,
                amount=opening_balance,
                description="Opening cash balance",
            )
        )

    await db.commit()
    await db.refresh(register)

    return register


async def calculate_expected_cash(
    db: AsyncSession,
    register: CashRegister,
) -> Decimal:
    result = await db.execute(
        select(CashMovement).where(
            CashMovement.cash_register_id == register.id,
        )
    )

    balance = Decimal("0")

    for movement in result.scalars().all():
        movement_type = str(movement.movement_type)
        amount = movement.amount

        if movement_type in {
            CashMovementType.OUT.value,
            CashMovementType.EXPENSE.value,
        }:
            balance -= amount
        else:
            balance += amount

    return balance


async def add_cash_movement(
    db: AsyncSession,
    register: CashRegister,
    user_id: uuid.UUID,
    amount: Decimal,
    movement_type: str,
    description: str | None = None,
) -> CashMovement:
    if not register.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash register is closed.",
        )

    movement = CashMovement(
        cash_register_id=register.id,
        user_id=user_id,
        movement_type=movement_type,
        amount=amount,
        description=description.strip()
        if description
        else None,
    )

    db.add(movement)
    await db.commit()
    await db.refresh(movement)

    return movement


async def close_cash_register(
    db: AsyncSession,
    register: CashRegister,
    user_id: uuid.UUID,
    actual_closing_balance: Decimal,
    notes: str | None = None,
) -> CashRegister:
    if not register.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash register is already closed.",
        )

    expected = await calculate_expected_cash(
        db,
        register,
    )

    register.expected_closing_balance = expected
    register.actual_closing_balance = actual_closing_balance
    register.difference = actual_closing_balance - expected
    register.closed_by = user_id
    register.is_open = False

    if notes:
        register.notes = notes.strip()

    await db.commit()
    await db.refresh(register)

    return register
