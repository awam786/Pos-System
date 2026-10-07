from __future__ import annotations

from enum import StrEnum

from app.models import Role


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    DASHBOARD = "dashboard"

    CREATE_SALE = "create_sale"
    SALES = "sales"
    VOID_SALE = "void_sale"
    VIEW_SALES = "view_sales"
    REPRINT_RECEIPT = "reprint_receipt"

    CREATE_RETURN = "create_return"
    VIEW_RETURNS = "view_returns"

    VIEW_PRODUCTS = "view_products"
    MANAGE_PRODUCTS = "manage_products"
    CREATE_PRODUCT = "create_product"
    EDIT_PRODUCT = "edit_product"
    ARCHIVE_PRODUCT = "archive_product"
    MANAGE_BARCODES = "manage_barcodes"
    ADJUST_STOCK = "adjust_stock"
    MANAGE_STOCK = "manage_stock"

    VIEW_PURCHASES = "view_purchases"
    CREATE_PURCHASE = "create_purchase"
    EDIT_PURCHASE = "edit_purchase"

    VIEW_CUSTOMERS = "view_customers"
    CUSTOMERS = "customers"
    MANAGE_CUSTOMERS = "manage_customers"
    RECEIVE_CUSTOMER_PAYMENT = "receive_customer_payment"

    VIEW_SUPPLIERS = "view_suppliers"
    SUPPLIERS = "suppliers"
    MANAGE_SUPPLIERS = "manage_suppliers"
    PAY_SUPPLIER = "pay_supplier"

    VIEW_EXPENSES = "view_expenses"
    CREATE_EXPENSE = "create_expense"
    MANAGE_EXPENSES = "manage_expenses"

    OPEN_REGISTER = "open_register"
    CLOSE_REGISTER = "close_register"
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"
    MANAGE_CASH_REGISTER = "manage_cash_register"

    VIEW_REPORTS = "view_reports"
    REPORTS = "reports"
    VIEW_PROFIT = "view_profit"

    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"

    MANAGE_SHOP = "manage_shop"
    MANAGE_RECEIPTS = "manage_receipts"

    VIEW_AUDIT_LOG = "view_audit_log"


OWNER_PERMISSIONS = frozenset(
    permission.value
    for permission in Permission
)


MANAGER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.DASHBOARD,

        Permission.CREATE_SALE,
        Permission.SALES,
        Permission.VOID_SALE,
        Permission.VIEW_SALES,
        Permission.REPRINT_RECEIPT,

        Permission.CREATE_RETURN,
        Permission.VIEW_RETURNS,

        Permission.VIEW_PRODUCTS,
        Permission.MANAGE_PRODUCTS,
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.ARCHIVE_PRODUCT,
        Permission.MANAGE_BARCODES,
        Permission.ADJUST_STOCK,
        Permission.MANAGE_STOCK,

        Permission.VIEW_PURCHASES,
        Permission.CREATE_PURCHASE,
        Permission.EDIT_PURCHASE,

        Permission.VIEW_CUSTOMERS,
        Permission.CUSTOMERS,
        Permission.MANAGE_CUSTOMERS,
        Permission.RECEIVE_CUSTOMER_PAYMENT,

        Permission.VIEW_SUPPLIERS,
        Permission.SUPPLIERS,
        Permission.MANAGE_SUPPLIERS,
        Permission.PAY_SUPPLIER,

        Permission.VIEW_EXPENSES,
        Permission.CREATE_EXPENSE,
        Permission.MANAGE_EXPENSES,

        Permission.OPEN_REGISTER,
        Permission.CLOSE_REGISTER,
        Permission.CASH_IN,
        Permission.CASH_OUT,
        Permission.MANAGE_CASH_REGISTER,

        Permission.VIEW_REPORTS,
        Permission.REPORTS,
        Permission.VIEW_PROFIT,

        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,

        Permission.MANAGE_SHOP,
        Permission.MANAGE_RECEIPTS,

        Permission.VIEW_AUDIT_LOG,
    }
)


CASHIER_PERMISSIONS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.DASHBOARD,

        Permission.CREATE_SALE,
        Permission.SALES,
        Permission.VIEW_SALES,
        Permission.REPRINT_RECEIPT,

        Permission.CREATE_RETURN,
        Permission.VIEW_RETURNS,

        Permission.VIEW_PRODUCTS,

        Permission.VIEW_CUSTOMERS,
        Permission.CUSTOMERS,
        Permission.MANAGE_CUSTOMERS,
        Permission.RECEIVE_CUSTOMER_PAYMENT,

        Permission.OPEN_REGISTER,
        Permission.CLOSE_REGISTER,
        Permission.CASH_IN,
        Permission.CASH_OUT,
        Permission.MANAGE_CASH_REGISTER,
    }
)


ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.OWNER: OWNER_PERMISSIONS,
    Role.MANAGER: frozenset(
        permission.value
        for permission in MANAGER_PERMISSIONS
    ),
    Role.CASHIER: frozenset(
        permission.value
        for permission in CASHIER_PERMISSIONS
    ),
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

    return permission_value in ROLE_PERMISSIONS.get(
        role,
        frozenset(),
    )
