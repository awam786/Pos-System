from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models import (
    CashMovement,
    CashMovementType,
    CashRegister,
    Expense,
    StockMovement,
)
from app.permissions import Permission
from app.schemas.inventory import (
    CashMovementCreate,
    CashRegisterCloseCreate,
    CashRegisterOpenCreate,
    CashRegisterResponse,
    ExpenseCreate,
    ExpenseResponse,
    StockAdjustmentCreate,
    StockMovementResponse,
    StockSummaryResponse,
)
from app.services.inventory import (
    add_cash_movement,
    adjust_stock,
    close_cash_register,
    create_expense,
    get_open_cash_register,
    get_product,
    open_cash_register,
)
from app.services.permissions import require_permission
from app.services.products import parse_uuid


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory & Cash"],
)


def stock_movement_response(
    movement: StockMovement,
) -> StockMovementResponse:
    return StockMovementResponse(
        id=str(movement.id),
        product_id=str(movement.product_id),
        movement_type=str(movement.movement_type),
        quantity=movement.quantity,
        balance_after=movement.balance_after,
        reference_type=movement.reference_type,
        reference_id=(
            str(movement.reference_id)
            if movement.reference_id
            else None
        ),
        notes=movement.notes,
        created_at=movement.created_at.isoformat(),
    )


def cash_register_response(
    register: CashRegister,
) -> CashRegisterResponse:
    return CashRegisterResponse(
        id=str(register.id),
        opening_balance=register.opening_balance,
        expected_closing_balance=register.expected_closing_balance,
        actual_closing_balance=register.actual_closing_balance,
        difference=register.difference,
        is_open=register.is_open,
        notes=register.notes,
        opened_by=str(register.opened_by),
        closed_by=(
            str(register.closed_by)
            if register.closed_by
            else None
        ),
        created_at=register.created_at.isoformat(),
    )


@router.post(
    "/stock-adjustments",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_adjustment(
    payload: StockAdjustmentCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.MANAGE_STOCK)

    product_id = parse_uuid(
        payload.product_id,
        "product_id",
    )

    movement = await adjust_stock(
        db,
        current_user.shop_id,
        current_user.id,
        product_id,
        payload.quantity,
        payload.notes,
    )

    return stock_movement_response(movement)


@router.get(
    "/stock/{product_id}",
    response_model=StockSummaryResponse,
)
async def get_stock(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    product = await get_product(
        db,
        current_user.shop_id,
        parse_uuid(product_id, "product_id"),
    )

    return StockSummaryResponse(
        product_id=str(product.id),
        stock_quantity=product.stock_quantity,
        minimum_stock=product.minimum_stock,
        maximum_stock=product.maximum_stock,
        low_stock=(
            product.stock_quantity <= product.minimum_stock
            and product.stock_quantity > 0
        ),
        out_of_stock=product.stock_quantity <= 0,
    )


@router.get(
    "/stock/{product_id}/movements",
    response_model=list[StockMovementResponse],
)
async def list_stock_movements(
    product_id: str,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
):
    product_uuid = parse_uuid(
        product_id,
        "product_id",
    )

    await get_product(
        db,
        current_user.shop_id,
        product_uuid,
    )

    result = await db.execute(
        select(StockMovement)
        .where(
            StockMovement.shop_id == current_user.shop_id,
            StockMovement.product_id == product_uuid,
        )
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
    )

    return [
        stock_movement_response(item)
        for item in result.scalars().all()
    ]


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_expense(
    payload: ExpenseCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_EXPENSES,
    )

    expense = await create_expense(
        db,
        current_user.shop_id,
        current_user.id,
        payload.category,
        payload.amount,
        payload.payment_method,
        payload.description,
        payload.reference,
    )

    return ExpenseResponse(
        id=str(expense.id),
        category=expense.category,
        amount=expense.amount,
        payment_method=expense.payment_method,
        description=expense.description,
        reference=expense.reference,
        created_at=expense.created_at.isoformat(),
    )


@router.get(
    "/expenses",
    response_model=list[ExpenseResponse],
)
async def list_expenses(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
):
    require_permission(
        current_user,
        Permission.MANAGE_EXPENSES,
    )

    result = await db.execute(
        select(Expense)
        .where(
            Expense.shop_id == current_user.shop_id,
        )
        .order_by(Expense.created_at.desc())
        .limit(limit)
    )

    return [
        ExpenseResponse(
            id=str(expense.id),
            category=expense.category,
            amount=expense.amount,
            payment_method=expense.payment_method,
            description=expense.description,
            reference=expense.reference,
            created_at=expense.created_at.isoformat(),
        )
        for expense in result.scalars().all()
    ]


@router.get(
    "/cash-register/current",
    response_model=CashRegisterResponse | None,
)
async def current_cash_register(
    db: DbSession,
    current_user: CurrentUser,
):
    register = await get_open_cash_register(
        db,
        current_user.shop_id,
    )

    if register is None:
        return None

    return cash_register_response(register)


@router.post(
    "/cash-register/open",
    response_model=CashRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_register(
    payload: CashRegisterOpenCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CASH_REGISTER,
    )

    register = await open_cash_register(
        db,
        current_user.shop_id,
        current_user.id,
        payload.opening_balance,
        payload.notes,
    )

    return cash_register_response(register)


@router.post("/cash-register/cash-in")
async def cash_in(
    payload: CashMovementCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CASH_REGISTER,
    )

    register = await get_open_cash_register(
        db,
        current_user.shop_id,
    )

    if register is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open cash register.",
        )

    movement = await add_cash_movement(
        db,
        register,
        current_user.id,
        payload.amount,
        CashMovementType.CASH_IN.value,
        payload.description,
    )

    return {
        "success": True,
        "movement_id": str(movement.id),
        "amount": movement.amount,
    }


@router.post("/cash-register/cash-out")
async def cash_out(
    payload: CashMovementCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CASH_REGISTER,
    )

    register = await get_open_cash_register(
        db,
        current_user.shop_id,
    )

    if register is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open cash register.",
        )

    movement = await add_cash_movement(
        db,
        register,
        current_user.id,
        payload.amount,
        CashMovementType.CASH_OUT.value,
        payload.description,
    )

    return {
        "success": True,
        "movement_id": str(movement.id),
        "amount": movement.amount,
    }


@router.post(
    "/cash-register/close",
    response_model=CashRegisterResponse,
)
async def close_register(
    payload: CashRegisterCloseCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CASH_REGISTER,
    )

    register = await get_open_cash_register(
        db,
        current_user.shop_id,
    )

    if register is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open cash register.",
        )

    register = await close_cash_register(
        db,
        register,
        current_user.id,
        payload.actual_closing_balance,
        payload.notes,
    )

    return cash_register_response(register)
