from __future__ import annotations

from enum import StrEnum

from app.models import Role


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"

    CREATE_SALE = "create_sale"
    VOID_SALE = "void_sale"
    VIEW_SALES = "view_sales"
    REPRINT_RECEIPT = "reprint_receipt"

    CREATE_RETURN = "create_return"
    VIEW_RETURNS = "view_returns"

    VIEW_PRODUCTS = "view_products"
    CREATE_PRODUCT = "create_product"
    EDIT_PRODUCT = "edit_product"
    ARCHIVE_PRODUCT = "archive_product"
    MANAGE_BARCODES = "manage_barcodes"
    ADJUST_STOCK = "adjust_stock"

    VIEW_PURCHASES = "view_purchases"
    CREATE_PURCHASE = "create_purchase"
    EDIT_PURCHASE = "edit_purchase"

    VIEW_CUSTOMERS = "view_customers"
    MANAGE_CUSTOMERS = "manage_customers"
    RECEIVE_CUSTOMER_PAYMENT = "receive_customer_payment"

    VIEW_SUPPLIERS = "view_suppliers"
    MANAGE_SUPPLIERS = "manage_suppliers"
    PAY_SUPPLIER = "pay_supplier"

    VIEW_EXPENSES = "view_expenses"
    CREATE_EXPENSE = "create_expense"

    OPEN_REGISTER = "open_register"
    CLOSE_REGISTER = "close_register"
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"

    VIEW_REPORTS = "view_reports"
    VIEW_PROFIT = "view_profit"

    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"

    MANAGE_SHOP = "manage_shop"
    MANAGE_RECEIPTS = "manage_receipts"

    VIEW_AUDIT_LOG = "view_audit_log"


OWNER_PERMISSIONS = frozenset(permission.value for permission in Permission)


MANAGER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.CREATE_SALE,
        Permission.VOID_SALE,
        Permission.VIEW_SALES,
        Permission.REPRINT_RECEIPT,
        Permission.CREATE_RETURN,
        Permission.VIEW_RETURNS,
        Permission.VIEW_PRODUCTS,
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.ARCHIVE_PRODUCT,
        Permission.MANAGE_BARCODES,
        Permission.ADJUST_STOCK,
        Permission.VIEW_PURCHASES,
        Permission.CREATE_PURCHASE,
        Permission.EDIT_PURCHASE,
        Permission.VIEW_CUSTOMERS,
        Permission.MANAGE_CUSTOMERS,
        Permission.RECEIVE_CUSTOMER_PAYMENT,
        Permission.VIEW_SUPPLIERS,
        Permission.MANAGE_SUPPLIERS,
        Permission.PAY_SUPPLIER,
        Permission.VIEW_EXPENSES,
        Permission.CREATE_EXPENSE,
        Permission.OPEN_REGISTER,
        Permission.CLOSE_REGISTER,
        Permission.CASH_IN,
        Permission.CASH_OUT,
        Permission.VIEW_REPORTS,
        Permission.VIEW_PROFIT,
    }
)


CASHIER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.CREATE_SALE,
        Permission.VIEW_SALES,
        Permission.REPRINT_RECEIPT,
        Permission.CREATE_RETURN,
        Permission.VIEW_PRODUCTS,
        Permission.VIEW_CUSTOMERS,
        Permission.MANAGE_CUSTOMERS,
        Permission.RECEIVE_CUSTOMER_PAYMENT,
        Permission.OPEN_REGISTER,
        Permission.CLOSE_REGISTER,
        Permission.CASH_IN,
        Permission.CASH_OUT,
    }
)


ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.OWNER: OWNER_PERMISSIONS,
    Role.MANAGER: frozenset(permission.value for permission in MANAGER_PERMISSIONS),
    Role.CASHIER: frozenset(permission.value for permission in CASHIER_PERMISSIONS),
}


def role_has_permission(
    role: Role,
    permission: Permission | str,
) -> bool:
    permission_value = (
        permission.value
        if isinstance(permission, Permission)
        else str(permission)
    )

    return permission_value in ROLE_PERMISSIONS.get(role, frozenset())
