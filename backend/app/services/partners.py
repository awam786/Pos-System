from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    CustomerPayment,
    Supplier,
    SupplierPayment,
)
from app.schemas.partner import (
    CustomerCreate,
    CustomerUpdate,
    PartnerPaymentCreate,
    SupplierCreate,
    SupplierUpdate,
)


def parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field_name}.",
        )


async def get_supplier(
    db: AsyncSession,
    shop_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Supplier:
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.shop_id == shop_id,
        )
    )

    supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found.",
        )

    return supplier


async def get_customer(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.shop_id == shop_id,
        )
    )

    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return customer


async def create_supplier(
    db: AsyncSession,
    shop_id: uuid.UUID,
    payload: SupplierCreate,
) -> Supplier:
    duplicate = await db.execute(
        select(Supplier).where(
            Supplier.shop_id == shop_id,
            Supplier.name == payload.name.strip(),
        )
    )

    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supplier with this name already exists.",
        )

    supplier = Supplier(
        shop_id=shop_id,
        name=payload.name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        email=payload.email.strip() if payload.email else None,
        address=payload.address.strip() if payload.address else None,
        opening_balance=payload.opening_balance,
        active=payload.active,
    )

    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    return supplier


async def update_supplier(
    db: AsyncSession,
    shop_id: uuid.UUID,
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
) -> Supplier:
    supplier = await get_supplier(
        db,
        shop_id,
        supplier_id,
    )

    values = payload.model_dump(exclude_unset=True)

    if "name" in values and values["name"] is not None:
        name = values["name"].strip()

        duplicate = await db.execute(
            select(Supplier).where(
                Supplier.shop_id == shop_id,
                Supplier.name == name,
                Supplier.id != supplier.id,
            )
        )

        if duplicate.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A supplier with this name already exists.",
            )

        supplier.name = name

    for field_name in (
        "phone",
        "email",
        "address",
    ):
        if field_name in values:
            value = values[field_name]
            setattr(
                supplier,
                field_name,
                value.strip() if isinstance(value, str) else value,
            )

    if "active" in values:
        supplier.active = values["active"]

    await db.commit()
    await db.refresh(supplier)

    return supplier


async def create_customer(
    db: AsyncSession,
    shop_id: uuid.UUID,
    payload: CustomerCreate,
) -> Customer:
    duplicate = await db.execute(
        select(Customer).where(
            Customer.shop_id == shop_id,
            Customer.name == payload.name.strip(),
            Customer.phone == (
                payload.phone.strip()
                if payload.phone
                else None
            ),
        )
    )

    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this name and phone already exists.",
        )

    customer = Customer(
        shop_id=shop_id,
        name=payload.name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        email=payload.email.strip() if payload.email else None,
        address=payload.address.strip() if payload.address else None,
        credit_limit=payload.credit_limit,
        opening_balance=payload.opening_balance,
        active=payload.active,
    )

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return customer


async def update_customer(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
) -> Customer:
    customer = await get_customer(
        db,
        shop_id,
        customer_id,
    )

    values = payload.model_dump(exclude_unset=True)

    if "name" in values and values["name"] is not None:
        customer.name = values["name"].strip()

    for field_name in (
        "phone",
        "email",
        "address",
    ):
        if field_name in values:
            value = values[field_name]

            setattr(
                customer,
                field_name,
                value.strip() if isinstance(value, str) else value,
            )

    if "credit_limit" in values:
        customer.credit_limit = values["credit_limit"]

    if "active" in values:
        customer.active = values["active"]

    await db.commit()
    await db.refresh(customer)

    return customer


async def record_customer_payment(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: PartnerPaymentCreate,
) -> CustomerPayment:
    customer = await get_customer(
        db,
        shop_id,
        customer_id,
    )

    if not customer.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payment for an inactive customer.",
        )

    payment = CustomerPayment(
        shop_id=shop_id,
        customer_id=customer.id,
        user_id=user_id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        reference=payload.reference.strip()
        if payload.reference
        else None,
        notes=payload.notes.strip()
        if payload.notes
        else None,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return payment


async def record_supplier_payment(
    db: AsyncSession,
    shop_id: uuid.UUID,
    supplier_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: PartnerPaymentCreate,
) -> SupplierPayment:
    supplier = await get_supplier(
        db,
        shop_id,
        supplier_id,
    )

    if not supplier.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payment for an inactive supplier.",
        )

    payment = SupplierPayment(
        shop_id=shop_id,
        supplier_id=supplier.id,
        user_id=user_id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        reference=payload.reference.strip()
        if payload.reference
        else None,
        notes=payload.notes.strip()
        if payload.notes
        else None,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return payment


async def customer_payment_total(
    db: AsyncSession,
    shop_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> Decimal:
    result = await db.execute(
        select(CustomerPayment.amount).where(
            CustomerPayment.shop_id == shop_id,
            CustomerPayment.customer_id == customer_id,
        )
    )

    return sum(
        (amount for amount in result.scalars().all()),
        Decimal("0"),
    )


async def supplier_payment_total(
    db: AsyncSession,
    shop_id: uuid.UUID,
    supplier_id: uuid.UUID,
) -> Decimal:
    result = await db.execute(
        select(SupplierPayment.amount).where(
            SupplierPayment.shop_id == shop_id,
            SupplierPayment.supplier_id == supplier_id,
        )
    )

    return sum(
        (amount for amount in result.scalars().all()),
        Decimal("0"),
    )
