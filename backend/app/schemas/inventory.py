from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class StockAdjustmentCreate(BaseModel):
    product_id: str
    quantity: Decimal
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Stock adjustment cannot be zero.")
        return value


class StockMovementResponse(BaseModel):
    id: str
    product_id: str
    movement_type: str
    quantity: Decimal
    balance_after: Decimal
    reference_type: str | None = None
    reference_id: str | None = None
    notes: str | None = None
    created_at: str


class StockSummaryResponse(BaseModel):
    product_id: str
    stock_quantity: Decimal
    minimum_stock: Decimal
    maximum_stock: Decimal | None = None
    low_stock: bool
    out_of_stock: bool


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    payment_method: str = Field(default="cash", min_length=1, max_length=30)
    description: str | None = Field(default=None, max_length=2000)
    reference: str | None = Field(default=None, max_length=150)

    @field_validator("category")
    @classmethod
    def clean_category(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Expense category cannot be empty.")

        return value

    @field_validator("payment_method")
    @classmethod
    def clean_payment_method(cls, value: str) -> str:
        value = value.strip().lower()

        allowed = {
            "cash",
            "bank_transfer",
            "card",
            "other",
        }

        if value not in allowed:
            raise ValueError(
                "Payment method must be cash, bank_transfer, card, or other."
            )

        return value


class ExpenseResponse(BaseModel):
    id: str
    category: str
    amount: Decimal
    payment_method: str
    description: str | None = None
    reference: str | None = None
    created_at: str


class CashRegisterOpenCreate(BaseModel):
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class CashMovementCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    description: str | None = Field(default=None, max_length=2000)


class CashRegisterCloseCreate(BaseModel):
    actual_closing_balance: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class CashRegisterResponse(BaseModel):
    id: str
    opening_balance: Decimal
    expected_closing_balance: Decimal | None = None
    actual_closing_balance: Decimal | None = None
    difference: Decimal | None = None
    is_open: bool
    notes: str | None = None
    opened_by: str
    closed_by: str | None = None
    created_at: str
