from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models import (
    Customer,
    CustomerPayment,
    Sale,
    Supplier,
    SupplierPayment,
    Purchase,
)
from app.permissions import Permission
from app.services.permissions import require_permission
from app.services.products import parse_uuid


router = APIRouter(
    prefix="/statements",
    tags=["Statements"],
)


@router.get("/customer/{customer_id}")
async def customer_statement(
    customer_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.CUSTOMERS)

    customer_uuid = parse_uuid(
        customer_id,
        "customer_id",
    )

    customer = await db.scalar(
        select(Customer).where(
            Customer.id == customer_uuid,
            Customer.shop_id == current_user.shop_id,
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    sales_result = await db.execute(
        select(Sale)
        .where(
            Sale.shop_id == current_user.shop_id,
            Sale.customer_id == customer.id,
            Sale.status != "voided",
        )
        .order_by(Sale.created_at.asc())
    )

    payment_result = await db.execute(
        select(CustomerPayment)
        .where(
            CustomerPayment.shop_id == current_user.shop_id,
            CustomerPayment.customer_id == customer.id,
        )
        .order_by(CustomerPayment.created_at.asc())
    )

    entries = []

    for sale in sales_result.scalars().all():
        entries.append(
            {
                "date": sale.created_at.isoformat(),
                "type": "sale",
                "reference": sale.receipt_number,
                "debit": Decimal(sale.total),
                "credit": Decimal("0"),
                "description": "Credit sale",
            }
        )

    for payment in payment_result.scalars().all():
        entries.append(
            {
                "date": payment.created_at.isoformat(),
                "type": "payment",
                "reference": str(payment.id),
                "debit": Decimal("0"),
                "credit": Decimal(payment.amount),
                "description": payment.notes or "Customer payment",
            }
        )

    entries.sort(key=lambda item: item["date"])

    opening = Decimal(customer.opening_balance or 0)
    balance = opening

    for entry in entries:
        balance += (
            Decimal(entry["debit"])
            - Decimal(entry["credit"])
        )
        entry["balance"] = balance

    return {
        "party": {
            "id": str(customer.id),
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "credit_limit": customer.credit_limit,
        },
        "opening_balance": opening,
        "total_debit": sum(
            (Decimal(e["debit"]) for e in entries),
            Decimal("0"),
        ),
        "total_credit": sum(
            (Decimal(e["credit"]) for e in entries),
            Decimal("0"),
        ),
        "closing_balance": balance,
        "entries": entries,
    }


@router.get("/supplier/{supplier_id}")
async def supplier_statement(
    supplier_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(current_user, Permission.SUPPLIERS)

    supplier_uuid = parse_uuid(
        supplier_id,
        "supplier_id",
    )

    supplier = await db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_uuid,
            Supplier.shop_id == current_user.shop_id,
        )
    )

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found.",
        )

    purchases_result = await db.execute(
        select(Purchase)
        .where(
            Purchase.shop_id == current_user.shop_id,
            Purchase.supplier_id == supplier.id,
            Purchase.status != "cancelled",
        )
        .order_by(Purchase.created_at.asc())
    )

    payment_result = await db.execute(
        select(SupplierPayment)
        .where(
            SupplierPayment.shop_id == current_user.shop_id,
            SupplierPayment.supplier_id == supplier.id,
        )
        .order_by(SupplierPayment.created_at.asc())
    )

    entries = []

    for purchase in purchases_result.scalars().all():
        entries.append(
            {
                "date": purchase.created_at.isoformat(),
                "type": "purchase",
                "reference": purchase.invoice_number,
                "debit": Decimal("0"),
                "credit": Decimal(purchase.total),
                "description": "Supplier purchase",
            }
        )

    for payment in payment_result.scalars().all():
        entries.append(
            {
                "date": payment.created_at.isoformat(),
                "type": "payment",
                "reference": str(payment.id),
                "debit": Decimal(payment.amount),
                "credit": Decimal("0"),
                "description": payment.notes or "Supplier payment",
            }
        )

    entries.sort(key=lambda item: item["date"])

    opening = Decimal(supplier.opening_balance or 0)
    balance = opening

    for entry in entries:
        balance += (
            Decimal(entry["credit"])
            - Decimal(entry["debit"])
        )
        entry["balance"] = balance

    return {
        "party": {
            "id": str(supplier.id),
            "name": supplier.name,
            "phone": supplier.phone,
            "email": supplier.email,
        },
        "opening_balance": opening,
        "total_purchases": sum(
            (Decimal(e["credit"]) for e in entries),
            Decimal("0"),
        ),
        "total_paid": sum(
            (Decimal(e["debit"]) for e in entries),
            Decimal("0"),
        ),
        "closing_balance": balance,
        "entries": entries,
    }
