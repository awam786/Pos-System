from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.dependencies import CurrentUser, DbSession
from app.models import Customer, CustomerPayment, Supplier, SupplierPayment
from app.permissions import Permission
from app.schemas.partner import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    PartnerPaymentCreate,
    PartnerPaymentResponse,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.partners import (
    create_customer,
    create_supplier,
    get_customer,
    get_supplier,
    parse_uuid,
    record_customer_payment,
    record_supplier_payment,
    update_customer,
    update_supplier,
)
from app.services.permissions import require_permission


router = APIRouter(
    prefix="/partners",
    tags=["Customers & Suppliers"],
)


def supplier_response(supplier: Supplier) -> SupplierResponse:
    return SupplierResponse(
        id=str(supplier.id),
        name=supplier.name,
        phone=supplier.phone,
        email=supplier.email,
        address=supplier.address,
        opening_balance=supplier.opening_balance,
        active=supplier.active,
    )


def customer_response(customer: Customer) -> CustomerResponse:
    return CustomerResponse(
        id=str(customer.id),
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        address=customer.address,
        credit_limit=customer.credit_limit,
        opening_balance=customer.opening_balance,
        active=customer.active,
    )


@router.get(
    "/suppliers",
    response_model=list[SupplierResponse],
)
async def list_suppliers(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    include_inactive: bool = False,
):
    query = select(Supplier).where(
        Supplier.shop_id == current_user.shop_id,
    )

    if not include_inactive:
        query = query.where(Supplier.active.is_(True))

    if search:
        term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Supplier.name.ilike(term),
                Supplier.phone.ilike(term),
                Supplier.email.ilike(term),
            )
        )

    query = query.order_by(Supplier.name.asc())

    result = await db.execute(query)

    return [
        supplier_response(supplier)
        for supplier in result.scalars().all()
    ]


@router.post(
    "/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_supplier(
    payload: SupplierCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_SUPPLIERS,
    )

    supplier = await create_supplier(
        db,
        current_user.shop_id,
        payload,
    )

    return supplier_response(supplier)


@router.get(
    "/suppliers/{supplier_id}",
    response_model=SupplierResponse,
)
async def get_supplier_detail(
    supplier_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    supplier = await get_supplier(
        db,
        current_user.shop_id,
        parse_uuid(supplier_id, "supplier_id"),
    )

    return supplier_response(supplier)


@router.patch(
    "/suppliers/{supplier_id}",
    response_model=SupplierResponse,
)
async def edit_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_SUPPLIERS,
    )

    supplier = await update_supplier(
        db,
        current_user.shop_id,
        parse_uuid(supplier_id, "supplier_id"),
        payload,
    )

    return supplier_response(supplier)


@router.post(
    "/suppliers/{supplier_id}/payments",
    response_model=PartnerPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_supplier_payment(
    supplier_id: str,
    payload: PartnerPaymentCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_SUPPLIERS,
    )

    payment = await record_supplier_payment(
        db,
        current_user.shop_id,
        parse_uuid(supplier_id, "supplier_id"),
        current_user.id,
        payload,
    )

    return PartnerPaymentResponse(
        id=str(payment.id),
        partner_id=str(payment.supplier_id),
        amount=payment.amount,
        payment_method=payment.payment_method,
        reference=payment.reference,
        notes=payment.notes,
    )


@router.get(
    "/customers",
    response_model=list[CustomerResponse],
)
async def list_customers(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    include_inactive: bool = False,
):
    query = select(Customer).where(
        Customer.shop_id == current_user.shop_id,
    )

    if not include_inactive:
        query = query.where(Customer.active.is_(True))

    if search:
        term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Customer.name.ilike(term),
                Customer.phone.ilike(term),
                Customer.email.ilike(term),
            )
        )

    query = query.order_by(Customer.name.asc())

    result = await db.execute(query)

    return [
        customer_response(customer)
        for customer in result.scalars().all()
    ]


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_customer(
    payload: CustomerCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CUSTOMERS,
    )

    customer = await create_customer(
        db,
        current_user.shop_id,
        payload,
    )

    return customer_response(customer)


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
)
async def get_customer_detail(
    customer_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    customer = await get_customer(
        db,
        current_user.shop_id,
        parse_uuid(customer_id, "customer_id"),
    )

    return customer_response(customer)


@router.patch(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
)
async def edit_customer(
    customer_id: str,
    payload: CustomerUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CUSTOMERS,
    )

    customer = await update_customer(
        db,
        current_user.shop_id,
        parse_uuid(customer_id, "customer_id"),
        payload,
    )

    return customer_response(customer)


@router.post(
    "/customers/{customer_id}/payments",
    response_model=PartnerPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_customer_payment(
    customer_id: str,
    payload: PartnerPaymentCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    require_permission(
        current_user,
        Permission.MANAGE_CUSTOMERS,
    )

    payment = await record_customer_payment(
        db,
        current_user.shop_id,
        parse_uuid(customer_id, "customer_id"),
        current_user.id,
        payload,
    )

    return PartnerPaymentResponse(
        id=str(payment.id),
        partner_id=str(payment.customer_id),
        amount=payment.amount,
        payment_method=payment.payment_method,
        reference=payment.reference,
        notes=payment.notes,
    )
