from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import (
    Expense,
    Product,
    Sale,
    SaleItem,
    StockMovement,
)
from app.permissions import Permission
from app.services.permissions import require_permission


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


def parse_date_range(
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime, datetime]:
    start = start_date or (date.today() - timedelta(days=29))
    end = end_date or date.today()

    if end < start:
        raise HTTPException(
            status_code=422,
            detail="end_date cannot be before start_date.",
        )

    return (
        datetime.combine(start, time.min),
        datetime.combine(end, time.max),
    )


@router.get("/dashboard")
async def dashboard_report(
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.DASHBOARD)

    today_start = datetime.combine(date.today(), time.min)
    tomorrow = today_start + timedelta(days=1)

    sales_result = await db.execute(
        select(
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total), 0),
            func.coalesce(func.sum(Sale.discount), 0),
            func.coalesce(func.sum(Sale.credit_amount), 0),
        ).where(
            Sale.shop_id == current_user.shop_id,
            Sale.created_at >= today_start,
            Sale.created_at < tomorrow,
            Sale.status != "voided",
        )
    )

    sales_count, sales_total, discount_total, credit_total = (
        sales_result.one()
    )

    product_count = await db.scalar(
        select(func.count(Product.id)).where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
        )
    )

    low_stock = await db.scalar(
        select(func.count(Product.id)).where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
            Product.stock_quantity <= Product.minimum_stock,
        )
    )

    expense_total = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.shop_id == current_user.shop_id,
            Expense.created_at >= today_start,
            Expense.created_at < tomorrow,
        )
    )

    return {
        "date": date.today().isoformat(),
        "sales_count": int(sales_count or 0),
        "sales_total": Decimal(sales_total or 0),
        "discount_total": Decimal(discount_total or 0),
        "credit_total": Decimal(credit_total or 0),
        "expense_total": Decimal(expense_total or 0),
        "active_products": int(product_count or 0),
        "low_stock_products": int(low_stock or 0),
    }


@router.get("/sales")
async def sales_report(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    require_permission(current_user, Permission.REPORTS)

    start, end = parse_date_range(
        start_date,
        end_date,
    )

    summary = await db.execute(
        select(
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.subtotal), 0),
            func.coalesce(func.sum(Sale.discount), 0),
            func.coalesce(func.sum(Sale.total), 0),
            func.coalesce(func.sum(Sale.paid_amount), 0),
            func.coalesce(func.sum(Sale.credit_amount), 0),
        ).where(
            Sale.shop_id == current_user.shop_id,
            Sale.created_at >= start,
            Sale.created_at <= end,
            Sale.status != "voided",
        )
    )

    (
        sale_count,
        subtotal,
        discount,
        total,
        paid,
        credit,
    ) = summary.one()

    daily_result = await db.execute(
        select(
            func.date(Sale.created_at).label("sale_date"),
            func.count(Sale.id).label("count"),
            func.coalesce(func.sum(Sale.total), 0).label("total"),
        )
        .where(
            Sale.shop_id == current_user.shop_id,
            Sale.created_at >= start,
            Sale.created_at <= end,
            Sale.status != "voided",
        )
        .group_by(func.date(Sale.created_at))
        .order_by(func.date(Sale.created_at))
    )

    daily = [
        {
            "date": str(row.sale_date),
            "count": int(row.count),
            "total": Decimal(row.total or 0),
        }
        for row in daily_result.all()
    ]

    return {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "summary": {
            "sale_count": int(sale_count or 0),
            "subtotal": Decimal(subtotal or 0),
            "discount": Decimal(discount or 0),
            "total": Decimal(total or 0),
            "paid": Decimal(paid or 0),
            "credit": Decimal(credit or 0),
        },
        "daily": daily,
    }


@router.get("/inventory")
async def inventory_report(
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.REPORTS)

    products = await db.execute(
        select(Product)
        .where(
            Product.shop_id == current_user.shop_id,
            Product.active.is_(True),
        )
        .order_by(Product.name.asc())
    )

    rows = []

    for product in products.scalars().all():
        stock_value = (
            Decimal(product.stock_quantity)
            * Decimal(product.purchase_price)
        )

        retail_value = (
            Decimal(product.stock_quantity)
            * Decimal(product.selling_price)
        )

        rows.append(
            {
                "product_id": str(product.id),
                "name": product.name,
                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "minimum_stock": product.minimum_stock,
                "purchase_price": product.purchase_price,
                "selling_price": product.selling_price,
                "stock_cost_value": stock_value,
                "stock_retail_value": retail_value,
                "low_stock": (
                    product.stock_quantity
                    <= product.minimum_stock
                ),
            }
        )

    return {
        "count": len(rows),
        "total_cost_value": sum(
            (row["stock_cost_value"] for row in rows),
            Decimal("0"),
        ),
        "total_retail_value": sum(
            (row["stock_retail_value"] for row in rows),
            Decimal("0"),
        ),
        "products": rows,
    }


@router.get("/profit")
async def profit_report(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    require_permission(current_user, Permission.REPORTS)

    start, end = parse_date_range(
        start_date,
        end_date,
    )

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(SaleItem.total),
                0,
            ).label("revenue"),
            func.coalesce(
                func.sum(
                    SaleItem.quantity
                    * Product.purchase_price
                ),
                0,
            ).label("cost"),
        )
        .join(
            Sale,
            Sale.id == SaleItem.sale_id,
        )
        .join(
            Product,
            Product.id == SaleItem.product_id,
        )
        .where(
            Sale.shop_id == current_user.shop_id,
            Sale.created_at >= start,
            Sale.created_at <= end,
            Sale.status != "voided",
        )
    )

    row = result.one()

    revenue = Decimal(row.revenue or 0)
    cost = Decimal(row.cost or 0)

    expense = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.shop_id == current_user.shop_id,
            Expense.created_at >= start,
            Expense.created_at <= end,
        )
    )

    expense = Decimal(expense or 0)

    return {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "revenue": revenue,
        "cost_of_goods": cost,
        "gross_profit": revenue - cost,
        "expenses": expense,
        "net_profit": revenue - cost - expense,
    }


@router.get("/stock-movements")
async def stock_movement_report(
    db: DbSession,
    current_user: CurrentUser,
    product_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    require_permission(current_user, Permission.REPORTS)

    statement = (
        select(
            StockMovement,
            Product.name,
            Product.sku,
        )
        .join(
            Product,
            Product.id == StockMovement.product_id,
        )
        .where(
            StockMovement.shop_id == current_user.shop_id,
        )
        .order_by(
            StockMovement.created_at.desc(),
        )
        .limit(limit)
    )

    if product_id:
        statement = statement.where(
            StockMovement.product_id == product_id
        )

    result = await db.execute(statement)

    return [
        {
            "id": str(movement.id),
            "product_id": str(movement.product_id),
            "product_name": name,
            "sku": sku,
            "movement_type": str(movement.movement_type),
            "quantity": movement.quantity,
            "balance_after": movement.balance_after,
            "reference_type": movement.reference_type,
            "reference_id": (
                str(movement.reference_id)
                if movement.reference_id
                else None
            ),
            "notes": movement.notes,
            "created_at": movement.created_at.isoformat(),
        }
        for movement, name, sku in result.all()
    ]
